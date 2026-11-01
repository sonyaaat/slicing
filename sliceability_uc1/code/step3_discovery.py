"""Step 3 - discovery on the discovery split only.

3a  notes.jsonl              P1, annotation model, one call per discovery prompt
3b  candidates_raw.json      P2, strong model, 3 rounds on notes + 2 rounds on raw text
3c  critique.json            P3 (+ P3b for missing attributes), strong model
3d  candidates_verified.json P5 on every cited evidence item, annotation model

The models see prompt text (or notes) and LOW/HIGH labels in 3b only. No score, answer,
axis or physician category reaches any prompt. The confirmation split is never read.

LOW / HIGH: target score <= its 25th percentile / >= its 75th percentile on the
discovery split (ties included on both sides; the run reports the resulting sizes).
"""

from __future__ import annotations

import json
import random
from collections import Counter

import numpy as np
import pandas as pd
import tiktoken

from annotate import annotate_one
from common import (OTHER, Run, die, has_prompt, load_prompt, log, norm_value, read_json,
                    read_jsonl, render, write_json, write_jsonl, write_meta)
from llm_client import LLM, LLMError, run_parallel


# ---------------------------------------------------------------------------
# shared
# ---------------------------------------------------------------------------

def load_discovery(run: Run) -> pd.DataFrame:
    df = pd.read_csv(run.path("uc1_data.csv"))
    if "split" not in df.columns:
        die("uc1_data.csv has no split column - run step 2 first")
    d = df[df.split == "discovery"].sort_values("prompt_id").reset_index(drop=True)
    pref = run.cfg["discovery"]["alias_prefix"]
    width = len(str(len(d)))
    d["alias"] = [f"{pref}{i + 1:0{max(3, width)}d}" for i in range(len(d))]
    return d


def contrast_groups(run: Run, d: pd.DataFrame) -> tuple[list[str], list[str], dict]:
    t = run.target
    q_lo = d[t].quantile(run.cfg["contrast"]["low_quantile"])
    q_hi = d[t].quantile(run.cfg["contrast"]["high_quantile"])
    low = d.loc[d[t] <= q_lo, "alias"].tolist()
    high = d.loc[d[t] >= q_hi, "alias"].tolist()
    if set(low) & set(high):
        die("LOW and HIGH overlap")
    info = {"target": t, "q_low": float(q_lo), "q_high": float(q_hi), "n_low": len(low),
            "n_high": len(high), "n_middle": len(d) - len(low) - len(high),
            "mean_low": float(d.loc[d.alias.isin(low), t].mean()),
            "mean_high": float(d.loc[d.alias.isin(high), t].mean())}
    return low, high, info


def notes_text(facts: list[str]) -> str:
    return " | ".join(str(f).strip() for f in facts)


# ---------------------------------------------------------------------------
# 3a notes
# ---------------------------------------------------------------------------

def step3a(run: Run, d: pd.DataFrame, llm: LLM, limit: int | None) -> dict[str, list[str]]:
    template, version = load_prompt(run, "P1")
    items = d if limit is None else d.head(limit)

    def validator(obj):
        if not isinstance(obj, dict) or not isinstance(obj.get("facts"), list) \
                or not obj["facts"] or not all(isinstance(f, str) and f.strip()
                                               for f in obj["facts"]):
            raise ValueError("reply has no non-empty 'facts' list of strings")
        return obj

    def one(row):
        p = render(template, prompt_id=row.alias, user_text=row.user_text)
        return llm.complete_json(p, step="3a", prompt_version=version, item=row.prompt_id,
                                 validator=validator)

    res = run_parallel(one, list(items.itertuples()), llm.n_slots, "3a notes", every=50)
    rows, notes, fails = [], {}, 0
    for row, r in zip(items.itertuples(), res):
        if isinstance(r, Exception):
            fails += 1
            rows.append({"prompt_id": row.prompt_id, "alias": row.alias, "facts": None,
                         "error": str(r)[:300]})
            continue
        facts = [str(f).strip() for f in r["facts"]]
        notes[row.alias] = facts
        rows.append({"prompt_id": row.prompt_id, "alias": row.alias, "facts": facts,
                     "n_facts": len(facts)})
    write_jsonl(run.path("notes.jsonl"), rows)
    nf = Counter(r.get("n_facts") for r in rows if r.get("facts"))
    write_meta(run, run.path("notes.jsonl"), "3a", model=llm.model, n_items=len(rows),
               n_failed=fails, n_facts_distribution=dict(sorted(nf.items())))
    log(f"3a: {len(notes)} notes, {fails} failed; facts per note {dict(sorted(nf.items()))}")
    if fails:
        log(f"3a WARNING: {fails} prompts have no notes and are excluded from notes rounds")
    return notes


# ---------------------------------------------------------------------------
# 3b induction
# ---------------------------------------------------------------------------

def _check_attr_list(atts, require_hypothesis: bool, where: str) -> None:
    for a in atts:
        if not isinstance(a, dict) or not a.get("name") or not a.get("question") \
                or not isinstance(a.get("values"), list):
            raise ValueError(f"malformed attribute in {where}: {str(a)[:150]}")
        if require_hypothesis and not str(a.get("hypothesis") or "").strip():
            raise ValueError(f"attribute {a.get('name')!r} in {where} has no hypothesis")
        for v in a["values"]:
            if not isinstance(v, dict) or "value" not in v:
                raise ValueError(f"malformed value in {a.get('name')}: {str(v)[:150]}")


def make_attr_validator(require_hypothesis: bool = False, allow_empty: bool = False):
    """Validator for a P2/P3b reply. require_hypothesis: run 2 rejects any attribute
    without one (and the reply is retried with a new cache salt). allow_empty: a
    cumulative round may legitimately find nothing new."""
    def check(obj):
        if not isinstance(obj, dict) or not isinstance(obj.get("attributes"), list) \
                or (not obj["attributes"] and not allow_empty):
            raise ValueError("reply has no non-empty 'attributes' list")
        _check_attr_list(obj["attributes"], require_hypothesis, "reply")
        return obj
    return check


_validate_attrs = make_attr_validator()


def _clean_candidate(a: dict, cid: str, rnd, shown: set[str], alias2pid: dict) -> dict:
    """Map aliases to prompt_ids, drop a model-listed 'other', flag ungrounded evidence."""
    gate = a.get("gate")
    gate = "all" if gate is None or norm_value(gate) in ("all", "") else str(gate).strip()
    values, removed = [], []
    for v in a["values"]:
        label = str(v["value"]).strip()
        if norm_value(label) == OTHER:
            removed.append({"value": label, "reason": "explicit 'other' (implicit in schema)"})
            continue
        ev = []
        seen = set()
        for e in v.get("evidence") or []:
            if not isinstance(e, dict):
                continue
            al = str(e.get("prompt_id", "")).strip()
            if al in seen:
                continue
            seen.add(al)
            ok = al in shown
            ev.append({"alias": al, "prompt_id": alias2pid.get(al) if ok else None,
                       "quote": e.get("quote"), "id_valid": ok})
        values.append({"value": label, "evidence": ev})
    return {"cid": cid, "round": rnd, "name": str(a["name"]).strip(),
            "question": str(a["question"]).strip(), "gate": gate, "values": values,
            "hypothesis": a.get("hypothesis"), "removed_values": removed}


def step3b(run: Run, d: pd.DataFrame, notes: dict, low: list, high: list,
           llm: LLM) -> list[dict]:
    cfg = run.cfg["discovery"]
    template, version = load_prompt(run, "P2")
    wording = run.cfg["contrast_wording"][run.target]
    alias2pid = dict(zip(d.alias, d.prompt_id))
    text_of = dict(zip(d.alias, d.user_text))
    enc = tiktoken.get_encoding(run.cfg["data"]["tokenizer"])

    def cut(t: str) -> str:
        toks = enc.encode(t)
        return t if len(toks) <= cfg["raw_max_tokens"] else enc.decode(toks[:cfg["raw_max_tokens"]])

    rounds = []
    low_n = [a for a in low if a in notes]
    high_n = [a for a in high if a in notes]
    for r in range(1, cfg["rounds_notes"] + 1):
        rng = random.Random(cfg["round_seed_base"] + r)
        lo, hi = low_n[:], high_n[:]
        rng.shuffle(lo); rng.shuffle(hi)
        rounds.append({"round": r, "kind": "notes", "seed": cfg["round_seed_base"] + r,
                       "low": lo, "high": hi,
                       "low_text": "\n".join(f"{a}: {notes_text(notes[a])}" for a in lo),
                       "high_text": "\n".join(f"{a}: {notes_text(notes[a])}" for a in hi),
                       "data_kind": "observations about user prompts"})
    # raw rounds: disjoint draws, no repeats between rounds
    k = cfg["raw_per_group"]
    rng = random.Random(cfg["round_seed_base"] + 100)
    lo_pool, hi_pool = low[:], high[:]
    rng.shuffle(lo_pool); rng.shuffle(hi_pool)
    if len(lo_pool) < k * cfg["rounds_raw"] or len(hi_pool) < k * cfg["rounds_raw"]:
        die("not enough LOW/HIGH prompts for disjoint raw rounds")
    for j in range(cfg["rounds_raw"]):
        r = cfg["rounds_notes"] + j + 1
        lo, hi = lo_pool[j * k:(j + 1) * k], hi_pool[j * k:(j + 1) * k]
        rounds.append({"round": r, "kind": "raw", "seed": cfg["round_seed_base"] + 100,
                       "low": lo, "high": hi,
                       "low_text": "\n\n".join(f"{a}: {cut(text_of[a])}" for a in lo),
                       "high_text": "\n\n".join(f"{a}: {cut(text_of[a])}" for a in hi),
                       "data_kind": f"user prompts, each cut to at most "
                                    f"{cfg['raw_max_tokens']} tokens"})

    cumulative = cfg.get("cumulative_rounds", False)
    req_h = cfg.get("require_hypothesis", False)
    so_far: list[dict] = []          # name + question of every attribute proposed so far

    def already_block() -> str:
        if not cumulative or not so_far:
            return ""
        lines = "\n".join(f"- {a['name']}: {a['question']}" for a in so_far)
        return ("=== ALREADY PROPOSED ===\n" + lines + "\n"
                "Propose attributes that are not in the list above and are not rewordings "
                "of them. If you cannot find 5 new ones, return fewer.")

    def one(rd):
        block = already_block()
        rd["n_already_proposed"] = len(so_far) if block else 0
        p = render(template, partition_description=run.cfg["partition_description"],
                   data_kind=rd["data_kind"], who_answered=wording["who"],
                   pronoun=wording["pronoun"], group_low=rd["low_text"],
                   group_high=rd["high_text"], already_proposed=block)
        rd["prompt_tokens_est"] = len(enc.encode(p))
        val = make_attr_validator(require_hypothesis=req_h,
                                  allow_empty=cumulative and bool(block))
        return llm.complete_json(p, step="3b", prompt_version=version,
                                 item=f"round{rd['round']}", validator=val)

    if cumulative:
        # each round sees what the earlier rounds proposed, so they run in order
        res = []
        for rd in rounds:
            try:
                r = one(rd)
            except Exception as e:                    # recorded below, then abort
                r = e
            res.append(r)
            if not isinstance(r, Exception):
                so_far.extend({"name": str(a["name"]).strip(),
                               "question": str(a["question"]).strip()}
                              for a in r["attributes"])
            log(f"  3b round {rd['round']}: "
                + (f"FAILED {r}" if isinstance(r, Exception)
                   else f"{len(r['attributes'])} attributes"))
            if isinstance(r, Exception):
                # later rounds depend on this one's attributes: stop, do not pay for them
                res += [LLMError("not run: an earlier cumulative round failed")] * (
                    len(rounds) - len(res))
                break
    else:
        res = run_parallel(one, rounds, len(rounds), "3b rounds", every=1)
    cands, round_log = [], []
    for rd, r in zip(rounds, res):
        entry = {k2: rd[k2] for k2 in ("round", "kind", "seed")}
        entry.update(n_low=len(rd["low"]), n_high=len(rd["high"]),
                     prompt_tokens_est=rd.get("prompt_tokens_est"),
                     n_already_proposed=rd.get("n_already_proposed", 0))
        if isinstance(r, Exception):
            entry["error"] = str(r)[:400]
            round_log.append(entry)
            log(f"3b round {rd['round']} FAILED: {r}")
            continue
        shown = set(rd["low"]) | set(rd["high"])
        entry["n_attributes"] = len(r["attributes"])
        entry["response"] = r
        round_log.append(entry)
        for i, a in enumerate(r["attributes"], 1):
            cands.append(_clean_candidate(a, f"r{rd['round']}_a{i}", rd["round"], shown,
                                          alias2pid))
    if any("error" in e for e in round_log):
        die("a 3b round failed after retries - see candidates_raw.json")

    # unique display names, so that 3c's duplicate_of is unambiguous
    seen = Counter()
    for c in cands:
        seen[norm_value(c["name"])] += 1
        c["display_name"] = c["name"] if seen[norm_value(c["name"])] == 1 else \
            f"{c['name']} ({seen[norm_value(c['name'])]})"
    out = {"rounds": round_log, "candidates": cands}
    write_json(run.path("candidates_raw.json"), out)
    write_meta(run, run.path("candidates_raw.json"), "3b", model=llm.model,
               temperature="model default (1); explicit temperature rejected by the API",
               n_candidates=len(cands))
    log(f"3b: {len(cands)} candidates from {len(rounds)} rounds "
        f"({[e.get('n_attributes') for e in round_log]})")
    return cands


# ---------------------------------------------------------------------------
# 3c critique
# ---------------------------------------------------------------------------

def _observations(d: pd.DataFrame, notes: dict, groups: dict | None = None) -> str:
    """One line per prompt. With groups (run 2), each line carries LOW / HIGH / MID."""
    if groups is None:
        return "\n".join(f"{a}: {notes_text(notes[a])}" for a in d.alias if a in notes)
    return "\n".join(f"{a} [{groups[a]}]: {notes_text(notes[a])}"
                     for a in d.alias if a in notes)


def step3c(run: Run, d: pd.DataFrame, notes: dict, cands: list[dict], llm: LLM,
           low: list | None = None, high: list | None = None) -> list[dict]:
    template, version = load_prompt(run, "P3")
    min_score = run.cfg["critique"]["min_score"]
    show = run.cfg["critique"].get("show_contrast", False)
    groups = None
    contrast_sentence = ""
    if show:
        lo_s, hi_s = set(low or []), set(high or [])
        groups = {a: ("LOW" if a in lo_s else "HIGH" if a in hi_s else "MID") for a in d.alias}
        w = run.cfg["contrast_wording"][run.target]
        contrast_sentence = (f"Group LOW: prompts where {w['who']} later answered poorly. "
                             "HIGH: answered well. MID: in between. You never see the answers.")
    obs = _observations(d, notes, groups)
    grounded_missing = not has_prompt(run, "P3b")
    req_h = run.cfg["discovery"].get("require_hypothesis", False)
    cand_json = json.dumps([{"name": c["display_name"], "question": c["question"],
                             "gate": c["gate"], "values": [v["value"] for v in c["values"]],
                             "hypothesis": c["hypothesis"], "round": c["round"]}
                            for c in cands], indent=1, ensure_ascii=False)
    by_name = {norm_value(c["display_name"]): c for c in cands}

    def validator(obj):
        if not isinstance(obj, dict) or not isinstance(obj.get("scores"), list):
            raise ValueError("reply has no 'scores' list")
        got = {norm_value(s.get("name")) for s in obj["scores"] if isinstance(s, dict)}
        missing = [c["display_name"] for c in cands if norm_value(c["display_name"]) not in got]
        if missing:
            raise ValueError(f"{len(missing)} candidates not scored, e.g. {missing[:3]}")
        for s in obj["scores"]:
            for k in ("concreteness", "distinctness", "plainness"):
                if not isinstance(s.get(k), (int, float)):
                    raise ValueError(f"score {k} missing for {s.get('name')}")
        if not isinstance(obj.get("missing", []), list):
            raise ValueError("'missing' is not a list")
        if grounded_missing:
            _check_attr_list(obj.get("missing") or [], req_h, "missing")
        return obj

    p = render(template, candidates=cand_json, observations=obs,
               contrast_sentence=contrast_sentence)
    crit = llm.complete_json(p, step="3c", prompt_version=version, item="critique",
                             validator=validator)

    scores = {}
    for s in crit["scores"]:
        n = norm_value(s.get("name"))
        if n in by_name and n not in scores:
            scores[n] = s
    # eligibility on concreteness and plainness; distinctness decides kept vs duplicate
    table = []
    for c in cands:
        s = scores[norm_value(c["display_name"])]
        c["critique"] = {k: s.get(k) for k in ("concreteness", "distinctness", "plainness",
                                                "duplicate_of", "note")}
        table.append(c)
    # Duplicate handling (rule refined 2026-10-15 after reading this step's output and
    # before any 3d result; recorded as a deviation in the report). Candidates passing
    # concreteness and plainness are "eligible". Every duplicate_of link between two
    # eligible candidates joins them into a group, in either direction. An eligible
    # candidate with distinctness < min_score is carried as "duplicate" if its group has
    # another member (step 4 merges the group into one attribute), and dropped otherwise.
    # The first version followed links in one direction only, so whether a member of a
    # duplicate pair survived depended on which way the critic happened to write the link.
    eligible = {c["cid"] for c in cands
                if c["critique"]["concreteness"] >= min_score
                and c["critique"]["plainness"] >= min_score}
    parent = {c["cid"]: c["cid"] for c in cands}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x

    for c in cands:
        tgt = by_name.get(norm_value(c["critique"].get("duplicate_of")))
        c["_dup_target"] = tgt
        if c["cid"] in eligible and tgt is not None and tgt["cid"] in eligible \
                and tgt["cid"] != c["cid"]:
            parent[find(c["cid"])] = find(tgt["cid"])
    group_size = Counter(find(c["cid"]) for c in cands if c["cid"] in eligible)
    for c in cands:
        cr = c["critique"]
        tgt = c.pop("_dup_target")
        low_dims = [k for k in ("concreteness", "plainness") if cr[k] < min_score]
        if low_dims:
            c["status_3c"] = "dropped"
            c["drop_reason_3c"] = "score < %d on %s" % (min_score, ", ".join(low_dims)) + \
                ("" if cr["distinctness"] >= min_score else " (and distinctness)")
            continue
        if tgt is not None and tgt["cid"] in eligible and tgt["cid"] != c["cid"]:
            c["duplicate_of_cid"] = tgt["cid"]
        if cr["distinctness"] >= min_score:
            c["status_3c"] = "kept"
        elif group_size[find(c["cid"])] > 1:
            c["status_3c"] = "duplicate"
            c["duplicate_group"] = find(c["cid"])
        else:
            c["status_3c"] = "dropped"
            c["drop_reason_3c"] = (f"distinctness < {min_score} and no eligible duplicate "
                                   f"partner (duplicate_of {cr.get('duplicate_of')!r}"
                                   + (", not eligible" if tgt is not None else
                                      ", not a candidate name" if cr.get("duplicate_of") else "")
                                   + ")")

    # missing attributes -> evidence call (P3b)
    missing = [m for m in (crit.get("missing") or []) if isinstance(m, dict)
               ][:run.cfg["critique"]["max_missing"]]
    added = []
    ev_raw = None
    if missing and grounded_missing:
        # run 2: P3 itself returns missing attributes with evidence, under P2's rule
        ev_raw = {"attributes": missing, "source": "P3 (no separate evidence call)"}
        alias2pid = dict(zip(d.alias, d.prompt_id))
        for i, a in enumerate(missing, 1):
            c = _clean_candidate(a, f"m{i}", "3c", set(notes), alias2pid)
            c["display_name"] = c["name"]
            c["status_3c"] = "added_missing"
            c["critique"] = None
            added.append(c)
    elif missing:
        t2, v2 = load_prompt(run, "P3b")
        attrs_json = json.dumps([{"name": m.get("name"), "question": m.get("question"),
                                  "values": m.get("values")} for m in missing],
                                indent=1, ensure_ascii=False)
        p2 = render(t2, attributes=attrs_json, observations=obs)
        try:
            ev_raw = llm.complete_json(p2, step="3c", prompt_version=v2,
                                       item="missing_evidence", validator=_validate_attrs)
        except LLMError as e:
            log(f"3c WARNING: evidence call for missing attributes failed: {e}")
            ev_raw = {"error": str(e)}
        shown = set(notes)
        alias2pid = dict(zip(d.alias, d.prompt_id))
        for i, a in enumerate((ev_raw or {}).get("attributes", []) or [], 1):
            c = _clean_candidate(a, f"m{i}", "3c", shown, alias2pid)
            c["display_name"] = c["name"]
            c["status_3c"] = "added_missing"
            c["critique"] = None
            added.append(c)

    out = {"min_score": min_score, "scores": [
        {"cid": c["cid"], "name": c["display_name"], "round": c["round"],
         **c["critique"], "status": c["status_3c"],
         "duplicate_of_cid": c.get("duplicate_of_cid"),
         "drop_reason": c.get("drop_reason_3c")} for c in cands],
        "missing": missing, "missing_with_evidence": added, "missing_evidence_raw": ev_raw,
        "raw_response": crit}
    write_json(run.path("critique.json"), out)
    write_meta(run, run.path("critique.json"), "3c", model=llm.model)
    st = Counter(c["status_3c"] for c in cands)
    log(f"3c: {dict(st)}; missing proposed {len(missing)}, added with evidence {len(added)}")
    return [c for c in cands if c["status_3c"] in ("kept", "duplicate")] + added


# ---------------------------------------------------------------------------
# 3d verification
# ---------------------------------------------------------------------------

def step3d(run: Run, d: pd.DataFrame, cands: list[dict], llm: LLM, limit: int | None) -> None:
    vcfg = run.cfg["verify"]
    seed = run.cfg["annotation"]["seed"]
    text = dict(zip(d.prompt_id, d.user_text))
    jobs = []
    for c in cands:
        attr = {"name": c["name"], "question": c["question"], "gate": c["gate"],
                "values": [v["value"] for v in c["values"]]}
        for vi, v in enumerate(c["values"]):
            for ei, e in enumerate(v["evidence"]):
                if e["id_valid"]:
                    jobs.append((c, attr, vi, ei, e["prompt_id"]))
    if limit is not None:
        jobs = jobs[:limit]
    log(f"3d: {len(jobs)} evidence items to verify for {len(cands)} candidates")

    def one(job):
        c, attr, vi, ei, pid = job
        return annotate_one(llm, run, attr, pid, text[pid], seed=seed, step="3d")

    res = run_parallel(one, jobs, llm.n_slots, "3d verify", every=100)
    verif = []
    for (c, attr, vi, ei, pid), r in zip(jobs, res):
        if isinstance(r, Exception):
            r = {"prompt_id": pid, "attribute": attr["name"], "value": "parse_error",
                 "error": str(r)[:300], "flags": "exception"}
        claimed = c["values"][vi]["value"]
        ok = norm_value(r["value"]) == norm_value(claimed)
        c["values"][vi]["evidence"][ei]["annotated_value"] = r["value"]
        c["values"][vi]["evidence"][ei]["confirmed"] = ok
        c["values"][vi]["evidence"][ei]["annotation_span"] = r.get("evidence_span")
        verif.append({"cid": c["cid"], "attribute": c["name"], "claimed": claimed, **r,
                      "confirmed": ok})

    kept, dropped = [], []
    for c in cands:
        for v in c["values"]:
            total = len(v["evidence"])
            n_valid = sum(e["id_valid"] for e in v["evidence"])
            conf = sum(bool(e.get("confirmed")) for e in v["evidence"])
            v["n_evidence"], v["n_valid_ids"], v["n_confirmed"] = total, n_valid, conf
            share = conf / total if total else 0.0
            v["confirmed_share"] = share
            if n_valid < vcfg["min_evidence_per_value"]:
                v["status"], v["drop_reason"] = "dropped", \
                    f"fewer than {vcfg['min_evidence_per_value']} evidence ids from the shown data"
            elif share < vcfg["min_evidence_confirmed"]:
                v["status"], v["drop_reason"] = "dropped", \
                    f"confirmed {conf}/{total} < {vcfg['min_evidence_confirmed']}"
            else:
                v["status"], v["drop_reason"] = "kept", None
        nk = sum(v["status"] == "kept" for v in c["values"])
        if nk < vcfg["min_values"]:
            c["status_3d"] = "dropped"
            c["drop_reason_3d"] = f"{nk} verified value(s) < {vcfg['min_values']}"
            dropped.append(c)
        else:
            c["status_3d"] = "kept"
            kept.append(c)
    out = {"rule": vcfg, "annotation_model": llm.model, "seed": seed,
           "attributes": kept, "dropped": dropped, "verification": verif}
    write_json(run.path("candidates_verified.json"), out)
    nconf = sum(v["confirmed"] for v in verif)
    write_meta(run, run.path("candidates_verified.json"), "3d", model=llm.model,
               n_calls=len(jobs), n_confirmed=nconf, n_kept=len(kept), n_dropped=len(dropped))
    log(f"3d: evidence confirmed {nconf}/{len(verif)}; attributes kept {len(kept)}, "
        f"dropped {len(dropped)}")


# ---------------------------------------------------------------------------

def run(run: Run, limit: int | None = None) -> None:
    d = load_discovery(run)
    low, high, info = contrast_groups(run, d)
    write_json(run.path("step3_contrast.json"), info)
    log(f"contrast on {info['target']}: LOW n={info['n_low']} (<= {info['q_low']:.4f}), "
        f"HIGH n={info['n_high']} (>= {info['q_high']:.4f}), middle {info['n_middle']}")
    ann = LLM(run, "annotation")
    strong = LLM(run, "strong")

    if run.path("notes.jsonl").exists() and limit is None:
        notes = {r["alias"]: r["facts"] for r in read_jsonl(run.path("notes.jsonl"))
                 if r.get("facts")}
        if len(notes) < len(d):
            notes = step3a(run, d, ann, limit)          # fill gaps from cache + API
    else:
        notes = step3a(run, d, ann, limit)
    cands = step3b(run, d, notes, low, high, strong)
    survivors = step3c(run, d, notes, cands, strong, low, high)
    step3d(run, d, survivors, ann, limit)
