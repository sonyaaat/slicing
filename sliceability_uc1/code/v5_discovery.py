"""Step 3 of the v5 corpus run (discovery split only).

3a notes.jsonl              P1, annotation model, one call per discovery message
3b candidates_raw.json      P2 v5, strong model, 5 cumulative rounds on notes; each round
                            70 LOW + 70 HIGH, 10 per theme per group, no repeats
3c critique.json            P3 v5, strong model, one call; notes of a 300-message sample
                            stratified by theme, each line marked LOW / HIGH / MID
3d candidates_verified.json P5 v5 on every cited evidence item; values kept at >= 50%
   thematic_pool.json       confirmed; attributes with >= 2 values and confirmed evidence
                            from >= 3 themes are universal, from 1-2 themes go to the pool

No model sees a score, an answer, a rubric, the theme name or a physician category. The
confirmation split is never loaded (v5_data.discovery_frame drops it).
"""

from __future__ import annotations

import json
import random
from collections import Counter, defaultdict

import pandas as pd
import tiktoken

from common import Run, die, load_prompt, log, norm_value, read_json, read_jsonl, render, \
    write_json, write_jsonl, write_meta
from step3_discovery import _clean_candidate, _check_attr_list, notes_text
from v5_annotate import annotate_one, canonical, is_absence_label
from v5_data import discovery_frame, theme_sample
from v5_infra import PROGRESS, V5LLM, decide, run_jobs


def contrast(run: Run, d: pd.DataFrame) -> tuple[list[str], list[str], dict]:
    t = run.cfg["target"]
    dd = d[d[t].notna()]
    q_lo = dd[t].quantile(run.cfg["contrast"]["low_quantile"])
    q_hi = dd[t].quantile(run.cfg["contrast"]["high_quantile"])
    low = dd.loc[dd[t] <= q_lo, "alias"].tolist()
    high = dd.loc[dd[t] >= q_hi, "alias"].tolist()
    if set(low) & set(high):
        die("LOW and HIGH overlap")
    th = dict(zip(d.alias, d.theme))
    info = {"target": t, "q_low": float(q_lo), "q_high": float(q_hi), "n_low": len(low),
            "n_high": len(high), "n_middle": int(len(dd) - len(low) - len(high)),
            "n_no_target": int(len(d) - len(dd)),
            "low_by_theme": dict(Counter(th[a] for a in low)),
            "high_by_theme": dict(Counter(th[a] for a in high))}
    return low, high, info


# ---------------------------------------------------------------------------
# 3a
# ---------------------------------------------------------------------------

def _notes_validator(obj):
    if not isinstance(obj, dict) or not isinstance(obj.get("facts"), list) or not obj["facts"] \
            or not all(isinstance(f, str) and f.strip() for f in obj["facts"]):
        raise ValueError("reply has no non-empty 'facts' list of strings")
    return obj


def notes_jobs(run: Run, d: pd.DataFrame, llm: V5LLM, step: str, rows) -> list[dict]:
    template, version = load_prompt(run, "P1")

    def one(row):
        p = render(template, prompt_id=row.alias, user_text=row.user_text)
        try:
            r = llm.complete_json(p, step="3a", prompt_version=version, item=row.prompt_id,
                                  validator=_notes_validator)
            return {"prompt_id": row.prompt_id, "alias": row.alias,
                    "facts": [str(f).strip() for f in r["facts"]], "n_facts": len(r["facts"])}
        except Exception as e:                        # LLMError after 3 attempts
            from v5_infra import FATAL
            if isinstance(e, FATAL):
                raise
            return {"prompt_id": row.prompt_id, "alias": row.alias, "facts": None,
                    "error": str(e)[:300], "_failed": True}

    return run_jobs(run, step, rows, lambda r: r.prompt_id, one, llm.n_slots, "3a notes",
                    every_log=200)


def step3a(run: Run, dry_run_n: int | None = None) -> None:
    d = discovery_frame(run)
    llm = V5LLM(run, "annotation")
    if dry_run_n:
        rows = list(d.head(dry_run_n).itertuples())
        res = notes_jobs(run, d, llm, "3a_dryrun", rows)
        write_jsonl(run.path("dryrun_3a.jsonl"), res)
        nf = Counter(r.get("n_facts") for r in res)
        log(f"3a dry run: {len(res)} items, {sum(1 for r in res if r.get('_failed'))} failed; "
            f"facts per note {dict(sorted(nf.items(), key=str))}")
        return
    rows = list(d.itertuples())
    res = notes_jobs(run, d, llm, "3a", rows)
    fails = [r for r in res if r.get("_failed")]
    write_jsonl(run.path("notes.jsonl"), res)
    nf = Counter(r.get("n_facts") for r in res if r.get("facts"))
    write_meta(run, run.path("notes.jsonl"), "3a", model=llm.model, n_items=len(res),
               n_failed=len(fails), n_facts_distribution={str(k): v for k, v in nf.items()})
    log(f"3a: {len(res) - len(fails)} notes, {len(fails)} failed")
    if fails:
        decide(run, "3a", f"{len(fails)} messages without notes are left out of 3b/3c",
               "P1 reply failed validation 3 times; the message is not shown in the contrast "
               "rounds or the critique sample (it is still annotated in steps 5-6)")
    if len(fails) > 0.05 * len(res):
        die(f"3a: {len(fails)} of {len(res)} notes failed (> 5%) - something is wrong")


def load_notes(run: Run) -> dict[str, list[str]]:
    return {r["alias"]: r["facts"] for r in read_jsonl(run.path("notes.jsonl")) if r.get("facts")}


# ---------------------------------------------------------------------------
# 3b
# ---------------------------------------------------------------------------

def build_rounds(run: Run, d: pd.DataFrame, notes: dict, low: list, high: list) -> list[dict]:
    cc = run.cfg["contrast"]
    k_theme, n_round = cc["per_theme_per_group"], run.cfg["discovery"]["rounds_notes"]
    th = dict(zip(d.alias, d.theme))
    themes = sorted(d.theme.unique())
    seed = cc["round_seed_base"]
    pools = {}
    for gname, grp in (("LOW", low), ("HIGH", high)):
        rng = random.Random(f"{seed}|{gname}")
        by = {t: [a for a in grp if a in notes and th[a] == t] for t in themes}
        for t in themes:
            rng.shuffle(by[t])
        pools[gname] = by
    rounds = []
    for r in range(1, n_round + 1):
        rd = {"round": r}
        for gname in ("LOW", "HIGH"):
            by = pools[gname]
            take = []
            short = 0
            for t in themes:
                got = by[t][:k_theme]
                by[t] = by[t][k_theme:]
                take += got
                if len(got) < k_theme:
                    short += k_theme - len(got)
                    decide(run, "3b", f"round {r} {gname}: theme {t} gives {len(got)} of {k_theme}",
                           f"pool of unused {gname} messages for this theme is exhausted (no "
                           "repeats between rounds); the shortfall is filled from other themes")
            while short:
                rest = sorted(themes, key=lambda t: -len(by[t]))
                if not by[rest[0]]:
                    decide(run, "3b", f"round {r} {gname}: {short} short of {cc['per_round']}",
                           "all theme pools exhausted")
                    break
                take.append(by[rest[0]].pop(0))
                short -= 1
            rng = random.Random(f"{seed}|order|{r}|{gname}")
            rng.shuffle(take)
            rd[gname.lower()] = take
            rd[f"{gname.lower()}_by_theme"] = dict(Counter(th[a] for a in take))
        rounds.append(rd)
    return rounds


def step3b(run: Run) -> None:
    d = discovery_frame(run)
    notes = load_notes(run)
    low, high, info = contrast(run, d)
    write_json(run.path("step3_contrast.json"), info)
    log(f"contrast on {info['target']}: LOW {info['n_low']} (<= {info['q_low']:.4f}), "
        f"HIGH {info['n_high']} (>= {info['q_high']:.4f}); LOW by theme {info['low_by_theme']}")
    rounds = build_rounds(run, d, notes, low, high)
    template, version = load_prompt(run, "P2")
    strong = V5LLM(run, "strong")
    alias2pid = dict(zip(d.alias, d.prompt_id))
    enc = tiktoken.get_encoding(run.cfg["data"]["tokenizer"])
    PROGRESS.add_total(len(rounds))
    so_far: list[dict] = []
    cands, round_log = [], []
    for rd in rounds:
        block = ""
        if so_far:
            block = ("=== ALREADY PROPOSED ===\n"
                     + "\n".join(f"- {a['name']}: {a['question']}" for a in so_far) + "\n"
                     "Propose attributes that are not in the list above and are not rewordings "
                     "of them. If you cannot find 5 new ones, return fewer.\n")
        p = render(template, partition_description=run.cfg["partition_description"],
                   group_low="\n".join(f"{a}: {notes_text(notes[a])}" for a in rd["low"]),
                   group_high="\n".join(f"{a}: {notes_text(notes[a])}" for a in rd["high"]),
                   already_proposed=block)
        allow_empty = bool(so_far)

        def val(obj):
            if not isinstance(obj, dict) or not isinstance(obj.get("attributes"), list) \
                    or (not obj["attributes"] and not allow_empty):
                raise ValueError("reply has no 'attributes' list")
            _check_attr_list(obj["attributes"], False, "reply")
            return obj

        r = strong.complete_json(p, step="3b", prompt_version=version,
                                 item=f"round{rd['round']}", validator=val)
        PROGRESS.job_done()
        shown = set(rd["low"]) | set(rd["high"])
        entry = {"round": rd["round"], "n_low": len(rd["low"]), "n_high": len(rd["high"]),
                 "low_by_theme": rd["low_by_theme"], "high_by_theme": rd["high_by_theme"],
                 "n_already_proposed": len(so_far), "prompt_tokens_est": len(enc.encode(p)),
                 "n_attributes": len(r["attributes"]), "response": r}
        round_log.append(entry)
        for i, a in enumerate(r["attributes"], 1):
            c = _clean_candidate(a, f"r{rd['round']}_a{i}", rd["round"], shown, alias2pid)
            cands.append(c)
        so_far += [{"name": str(a["name"]).strip(), "question": str(a["question"]).strip()}
                   for a in r["attributes"]]
        log(f"  3b round {rd['round']}: {len(r['attributes'])} attributes: "
            f"{[a['name'] for a in r['attributes']]}")
    seen = Counter()
    for c in cands:
        seen[norm_value(c["name"])] += 1
        c["display_name"] = c["name"] if seen[norm_value(c["name"])] == 1 else \
            f"{c['name']} ({seen[norm_value(c['name'])]})"
    write_json(run.path("candidates_raw.json"), {"rounds": round_log, "candidates": cands})
    write_meta(run, run.path("candidates_raw.json"), "3b", model=strong.model,
               temperature="model default (1); explicit temperature rejected by the API",
               n_candidates=len(cands))
    log(f"3b: {len(cands)} candidates from {len(rounds)} rounds")


# ---------------------------------------------------------------------------
# 3c
# ---------------------------------------------------------------------------

def step3c(run: Run) -> None:
    cc = run.cfg["critique"]
    d = discovery_frame(run)
    notes = load_notes(run)
    low, high, _ = contrast(run, d)
    cands = read_json(run.path("candidates_raw.json"))["candidates"]
    sample = set(theme_sample(d[d.alias.isin(notes)], cc["notes_sample"], cc["seed"]))
    ds = d[d.prompt_id.isin(sample)]
    lo_s, hi_s = set(low), set(high)
    grp = {a: ("LOW" if a in lo_s else "HIGH" if a in hi_s else "MID") for a in ds.alias}
    obs = "\n".join(f"{a} [{grp[a]}]: {notes_text(notes[a])}" for a in ds.alias)
    contrast_sentence = ("Group LOW: messages where two different assistants later answered "
                         "poorly. HIGH: answered well. MID: in between. You never see the answers.")
    template, version = load_prompt(run, "P3")
    cand_json = json.dumps([{"name": c["display_name"], "question": c["question"],
                             "values": [v["value"] for v in c["values"]], "round": c["round"]}
                            for c in cands], indent=1, ensure_ascii=False)
    by_name = {norm_value(c["display_name"]): c for c in cands}
    scores_k = cc["scores"]

    def validator(obj):
        if not isinstance(obj, dict) or not isinstance(obj.get("scores"), list):
            raise ValueError("reply has no 'scores' list")
        got = {norm_value(s.get("name")) for s in obj["scores"] if isinstance(s, dict)}
        miss = [c["display_name"] for c in cands if norm_value(c["display_name"]) not in got]
        if miss:
            raise ValueError(f"{len(miss)} candidates not scored, e.g. {miss[:3]}")
        for s in obj["scores"]:
            if not isinstance(s, dict):
                continue
            for k in scores_k:
                if not isinstance(s.get(k), (int, float)):
                    raise ValueError(f"score {k} missing for {s.get('name')}")
        if not isinstance(obj.get("missing", []), list):
            raise ValueError("'missing' is not a list")
        _check_attr_list(obj.get("missing") or [], False, "missing")
        return obj

    p = render(template, candidates=cand_json, observations=obs,
               contrast_sentence=contrast_sentence)
    strong = V5LLM(run, "strong")
    PROGRESS.add_total(1)
    crit = strong.complete_json(p, step="3c", prompt_version=version, item="critique",
                                validator=validator)
    PROGRESS.job_done()
    min_score = cc["min_score"]
    sc = {}
    for s in crit["scores"]:
        n = norm_value(s.get("name"))
        if n in by_name and n not in sc:
            sc[n] = s
    for c in cands:
        s = sc[norm_value(c["display_name"])]
        c["critique"] = {k: s.get(k) for k in scores_k + ["duplicate_of", "note"]}
    # Same duplicate logic as run 4 (step3_discovery.step3c), with breadth added to the
    # eligibility scores. factor is reported, not filtered (spec 3c: four scores, factor in
    # the risk table as a reported score).
    filt = cc["filter_scores"]
    eligible = {c["cid"] for c in cands if all(c["critique"][k] >= min_score for k in filt)}
    parent = {c["cid"]: c["cid"] for c in cands}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x

    for c in cands:
        tgt = by_name.get(norm_value(c["critique"].get("duplicate_of")))
        c["_dup"] = tgt
        if c["cid"] in eligible and tgt is not None and tgt["cid"] in eligible \
                and tgt["cid"] != c["cid"]:
            parent[find(c["cid"])] = find(tgt["cid"])
    gsize = Counter(find(c["cid"]) for c in cands if c["cid"] in eligible)
    for c in cands:
        cr = c["critique"]
        tgt = c.pop("_dup")
        low_dims = [k for k in filt if cr[k] < min_score]
        if low_dims:
            c["status_3c"] = "dropped"
            c["drop_reason_3c"] = f"score < {min_score} on {', '.join(low_dims)}"
            continue
        if tgt is not None and tgt["cid"] in eligible and tgt["cid"] != c["cid"]:
            c["duplicate_of_cid"] = tgt["cid"]
        if cr["distinctness"] >= min_score:
            c["status_3c"] = "kept"
        elif gsize[find(c["cid"])] > 1:
            c["status_3c"] = "duplicate"
        else:
            c["status_3c"] = "dropped"
            c["drop_reason_3c"] = (f"distinctness < {min_score} and no eligible duplicate partner "
                                   f"(duplicate_of {cr.get('duplicate_of')!r})")
    alias2pid = dict(zip(d.alias, d.prompt_id))
    missing = [m for m in (crit.get("missing") or []) if isinstance(m, dict)][:cc["max_missing"]]
    added = []
    for i, a in enumerate(missing, 1):
        c = _clean_candidate(a, f"m{i}", "3c", set(ds.alias), alias2pid)
        c["display_name"] = c["name"]
        c["status_3c"] = "added_missing"
        c["critique"] = None
        added.append(c)
    out = {"min_score": min_score, "filter_scores": filt, "sample_n": len(ds),
           "sample_by_theme": ds.theme.value_counts().to_dict(),
           "sample_groups": dict(Counter(grp.values())),
           "scores": [{"cid": c["cid"], "name": c["display_name"], "round": c["round"],
                       **c["critique"], "status": c["status_3c"],
                       "duplicate_of_cid": c.get("duplicate_of_cid"),
                       "drop_reason": c.get("drop_reason_3c")} for c in cands],
           "missing_with_evidence": added, "raw_response": crit,
           "survivors": [c for c in cands if c["status_3c"] in ("kept", "duplicate")] + added}
    write_json(run.path("critique.json"), out)
    write_meta(run, run.path("critique.json"), "3c", model=strong.model)
    log(f"3c: {dict(Counter(c['status_3c'] for c in cands))}; missing added {len(added)}")


# ---------------------------------------------------------------------------
# 3d
# ---------------------------------------------------------------------------

def step3d(run: Run, limit: int | None = None) -> None:
    vc = run.cfg["verify"]
    seed = run.cfg["annotation"]["seed"]
    d = discovery_frame(run)
    text = dict(zip(d.prompt_id, d.user_text))
    theme = dict(zip(d.prompt_id, d.theme))
    cands = read_json(run.path("critique.json"))["survivors"]
    llm = V5LLM(run, "annotation")
    jobs = []
    for ci, c in enumerate(cands):
        attr = {"name": c["name"], "question": c["question"],
                "values": [v["value"] for v in c["values"]]}
        for vi, v in enumerate(c["values"]):
            for ei, e in enumerate(v["evidence"]):
                if e["id_valid"]:
                    jobs.append((ci, attr, vi, ei, e["prompt_id"]))
    if limit:
        jobs = jobs[:limit]
    log(f"3d: {len(jobs)} evidence items for {len(cands)} candidates")

    def one(job):
        ci, attr, vi, ei, pid = job
        return annotate_one(llm, run, attr, pid, text[pid], seed=seed, step="3d")

    res = run_jobs(run, "3d", jobs, lambda j: f"{cands[j[0]]['cid']}|{j[2]}|{j[3]}|{j[4]}",
                   one, llm.n_slots, "3d verify", every_log=200)
    verif = []
    for (ci, attr, vi, ei, pid), r in zip(jobs, res):
        c = cands[ci]
        claimed = c["values"][vi]["value"]
        ok = canonical(r["value"]) == canonical(claimed)
        e = c["values"][vi]["evidence"][ei]
        e.update(annotated_value=r["value"], confirmed=ok, theme=theme[pid])
        verif.append({"cid": c["cid"], "attribute": c["name"], "claimed": claimed,
                      "prompt_id": pid, "theme": theme[pid], "value": r["value"],
                      "flags": r.get("flags"), "confirmed": ok})
    universal, pool, dropped = [], [], []
    for c in cands:
        for v in c["values"]:
            total = len(v["evidence"])
            n_valid = sum(e["id_valid"] for e in v["evidence"])
            conf = sum(bool(e.get("confirmed")) for e in v["evidence"])
            v.update(n_evidence=total, n_valid_ids=n_valid, n_confirmed=conf,
                     confirmed_share=conf / total if total else 0.0,
                     is_absence=is_absence_label(v["value"]))
            if n_valid < vc["min_evidence_per_value"]:
                v["status"], v["drop_reason"] = "dropped", \
                    f"fewer than {vc['min_evidence_per_value']} evidence ids from the shown data"
            elif v["confirmed_share"] < vc["min_evidence_confirmed"]:
                v["status"], v["drop_reason"] = "dropped", \
                    f"confirmed {conf}/{total} < {vc['min_evidence_confirmed']}"
            else:
                v["status"], v["drop_reason"] = "kept", None
        kept_vals = [v for v in c["values"] if v["status"] == "kept"]
        themes = sorted({e["theme"] for v in kept_vals for e in v["evidence"] if e.get("confirmed")})
        c["evidence_themes"] = themes
        c["n_evidence_themes"] = len(themes)
        if len(kept_vals) < vc["min_values"]:
            c["status_3d"], c["drop_reason_3d"] = "dropped", \
                f"{len(kept_vals)} verified value(s) < {vc['min_values']}"
            dropped.append(c)
        elif len(themes) < vc["min_themes"]:
            c["status_3d"], c["drop_reason_3d"] = "thematic_pool", \
                f"confirmed evidence from {len(themes)} theme(s) < {vc['min_themes']}: {themes}"
            pool.append(c)
        else:
            c["status_3d"] = "universal"
            universal.append(c)
    for c in pool:
        decide(run, "3d", f"'{c['name']}' -> thematic pool", c["drop_reason_3d"])
    write_json(run.path("candidates_verified.json"),
               {"rule": vc, "annotation_model": llm.model, "seed": seed,
                "attributes": universal, "thematic_pool": pool, "dropped": dropped,
                "verification": verif})
    write_json(run.path("thematic_pool.json"),
               {"attributes": [{"name": c["name"], "question": c["question"],
                                "values": [v["value"] for v in c["values"] if v["status"] == "kept"],
                                "source": "3d", "reason": c["drop_reason_3d"],
                                "evidence_themes": c["evidence_themes"]} for c in pool]})
    nconf = sum(v["confirmed"] for v in verif)
    write_meta(run, run.path("candidates_verified.json"), "3d", model=llm.model,
               n_calls=len(jobs), n_confirmed=nconf, n_universal=len(universal),
               n_pool=len(pool), n_dropped=len(dropped))
    log(f"3d: evidence confirmed {nconf}/{len(verif)}; universal {len(universal)}, "
        f"thematic pool {len(pool)}, dropped {len(dropped)}")
