"""Step 4 - merge verified candidates into one attribute per underlying property.

1. Embed "name. question" of every verified candidate with a local sentence-embedding
   model (run_config merge.embedding_model).
2. Agglomerative clustering on cosine distance, linkage from run_config (complete:
   every pair inside a cluster has cosine >= threshold).
3. The 3c duplicate links (candidate X "duplicate_of" Y) are unioned in, so a duplicate
   always lands in its target's cluster - this is how "duplicates are merged into the
   one they point to" is carried out.
4. One strong-model call (P4) for all clusters with more than one member. Singletons
   pass unchanged. The reply is checked: every value must cite evidence from the
   cluster's VERIFIED evidence; a value that does not is removed and logged.

Output candidates_merged.json: same schema as 3b, plus merged_from.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict

import numpy as np

from common import Run, die, load_prompt, log, norm_value, read_json, render, write_json, write_meta
from llm_client import LLM


def _embed(texts: list[str], model_name: str) -> tuple[np.ndarray, dict]:
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(model_name, device="cpu")
    emb = m.encode(texts, normalize_embeddings=True, batch_size=16, show_progress_bar=False)
    info = {"model": model_name}
    try:
        import glob, os
        snap = glob.glob(os.path.expanduser(
            f"~/.cache/huggingface/hub/models--{model_name.replace('/', '--')}/refs/main"))
        if snap:
            info["revision"] = open(snap[0]).read().strip()
    except Exception:
        pass
    info["dim"] = int(emb.shape[1])
    return np.asarray(emb), info


class _UF:
    def __init__(self, n): self.p = list(range(n))
    def find(self, i):
        while self.p[i] != i:
            self.p[i] = self.p[self.p[i]]; i = self.p[i]
        return i
    def union(self, a, b): self.p[self.find(a)] = self.find(b)


def _verified_view(c: dict) -> dict:
    """A candidate as the merge model sees it: kept values, confirmed evidence only."""
    vals = []
    for v in c["values"]:
        if v["status"] != "kept":
            continue
        ev = [{"prompt_id": e["alias"], "quote": e["quote"]} for e in v["evidence"]
              if e.get("confirmed")]
        vals.append({"value": v["value"], "evidence": ev})
    return {"name": c["display_name"], "question": c["question"], "gate": c["gate"],
            "values": vals, "hypothesis": c.get("hypothesis")}


_OR = re.compile(r"\bor\b", re.I)


def label_violations(a: dict, max_words: int, max_values: int) -> list[str]:
    """Run-2 P4 limits: <= max_words words, no comma, no 'or', <= max_values values."""
    out = []
    vals = [v for v in a.get("values", []) if norm_value(v.get("value")) != "other"]
    if len(vals) > max_values:
        out.append(f"{a.get('name')}: {len(vals)} values > {max_values}")
    for v in vals:
        lab = str(v.get("value", ""))
        if "," in lab or _OR.search(lab) or len(lab.split()) > max_words:
            out.append(f"{a.get('name')}: label {lab!r}")
    return out


def truncate_label(label: str, max_words: int) -> str:
    """Mechanical fix: first clause (before the first comma or 'or'), then max_words words."""
    first = re.split(r",|\bor\b", label, maxsplit=1, flags=re.I)[0].strip()
    return " ".join((first or label).split()[:max_words])


# ---------------------------------------------------------------------------
# Run 3: every attribute through P4 (merge.apply_limits_to_all)
# ---------------------------------------------------------------------------

NONE_LABEL = "none of these"
_NONE_FORMS = {"none of these", "none", "other", "neither", "none of the above",
               "none of the listed", "none listed"}


def is_other_type(label: str) -> bool:
    """Old label that begins with 'other' or means 'none of the listed'."""
    n = norm_value(label)
    return n.startswith("other") or n in _NONE_FORMS or "none of" in n


def _pick(d: dict, keys) -> str | None:
    for k in keys:
        if isinstance(d.get(k), str) and d[k].strip():
            return d[k].strip()
    return None


def _norm_reply_values(a: dict) -> list[dict]:
    """[{old, new, evidence}] from a P4 reply value list, whatever the key names."""
    out = []
    for v in a.get("values") or []:
        if not isinstance(v, dict):
            continue
        old = _pick(v, ("old_label", "old", "original_label", "previous_label", "old_value"))
        new = _pick(v, ("new_label", "new", "label", "new_value", "value"))
        out.append({"old": old, "new": new, "evidence": v.get("evidence") or []})
    return out


def _limit_violations_v3(atts: list[dict], max_words: int, max_values: int) -> list[str]:
    out = []
    for a in atts:
        vals = [v for v in _norm_reply_values(a) if v["new"] and not is_other_type(v["old"] or "")
                and not is_other_type(v["new"])]
        if len(vals) > max_values:
            out.append(f"{a.get('name')}: {len(vals)} values > {max_values}")
        for v in vals:
            lab = v["new"]
            if "," in lab or _OR.search(lab) or len(lab.split()) > max_words:
                out.append(f"{a.get('name')}: label {lab!r}")
    return out


def relabel_all(run: Run, cands: list[dict], clusters: list[list[int]], sim) -> dict:
    mc = run.cfg["merge"]
    max_words, max_values = mc["label_max_words"], mc["max_values"]
    template, version = load_prompt(run, "P4")
    groups = [{"group": g + 1, "candidates": [_verified_view(cands[i]) for i in ix]}
              for g, ix in enumerate(clusters)]
    p = render(template, groups=json.dumps(groups, indent=1, ensure_ascii=False))

    def validator(obj):
        atts = obj.get("attributes") if isinstance(obj, dict) else obj
        if not isinstance(atts, list) or len(atts) != len(clusters):
            raise ValueError(f"expected {len(clusters)} attributes, got "
                             f"{len(atts) if isinstance(atts, list) else type(atts)}")
        for a in atts:
            if not isinstance(a, dict) or not a.get("name") or \
                    not isinstance(a.get("values"), list) or not isinstance(a.get("merged_from"), list):
                raise ValueError(f"malformed attribute {str(a)[:150]}")
            vs = _norm_reply_values(a)
            if not vs or any(not v["old"] or not v["new"] for v in vs):
                raise ValueError(f"attribute {a.get('name')!r}: a value lacks the old or new label")
        return atts

    strong = LLM(run, "strong")
    raw = strong.complete_json(p, step="4", prompt_version=version, item="relabel",
                               validator=validator)
    viol = _limit_violations_v3(raw, max_words, max_values)
    limit_log = {"enforced": True, "applied_to": "all attributes",
                 "violations_first_reply": viol}
    for k in range(mc.get("limit_violation_retries", 1)):
        if not viol:
            break
        log(f"4: relabel reply violates the limits ({len(viol)}); retry {k + 1}")
        raw = strong.complete_json(p, step="4", prompt_version=version, item="relabel",
                                   validator=validator, salt_prefix=f"limits{k + 1}")
        viol = _limit_violations_v3(raw, max_words, max_values)
        limit_log[f"violations_retry{k + 1}"] = viol
    mech = bool(viol)
    limit_log["mechanical_fix_needed"] = mech

    merged, label_map, used = [], [], set()
    for g, ix in enumerate(clusters):
        names = {norm_value(cands[i]["display_name"]) for i in ix} | \
                {norm_value(cands[i]["name"]) for i in ix}
        best, best_ov = None, -1
        for k, a in enumerate(raw):
            if k in used:
                continue
            ov = len(names & {norm_value(x) for x in a["merged_from"]}) + \
                (1 if norm_value(a.get("name")) in names else 0)
            if ov > best_ov:
                best, best_ov = k, ov
        if best_ov <= 0:
            die(f"relabel reply has no attribute matching group {g + 1}")
        used.add(best)
        a = raw[best]
        single = len(ix) == 1
        c0 = cands[ix[0]]
        # member values (kept at 3d) with their verified evidence, by normalised label
        member = {}
        for i in ix:
            for v in cands[i]["values"]:
                if v["status"] == "kept":
                    member.setdefault(norm_value(v["value"]), {"label": v["value"], "evidence": []})
                    member[norm_value(v["value"])]["evidence"] += [
                        {"alias": e["alias"], "prompt_id": e["prompt_id"], "quote": e["quote"]}
                        for e in v["evidence"] if e.get("confirmed")]
        seen_old = set()
        new_vals: dict[str, dict] = {}
        as_other_old = []
        for v in _norm_reply_values(a):
            m = member.get(norm_value(v["old"]))
            old = m["label"] if m else v["old"]
            if m is None:
                label_map.append({"attribute": c0["name"], "old_label": v["old"],
                                  "new_label": v["new"], "how": "dropped: old label is not a "
                                  "verified value of this attribute"})
                continue
            seen_old.add(norm_value(old))
            # other-type if the OLD label is, or if the reply's NEW label is (a model-written
            # "Other: ..." label must not survive as a separate value)
            if is_other_type(old) or is_other_type(v["new"]):
                as_other_old.append(old)
                label_map.append({"attribute": c0["name"], "old_label": old,
                                  "new_label": NONE_LABEL, "how": "other-type -> treated as other"})
                continue
            new, how = v["new"], ("unchanged" if norm_value(v["new"]) == norm_value(old) else "model")
            if mech and ("," in new or _OR.search(new) or len(new.split()) > max_words):
                new, how = truncate_label(new, max_words), "mechanical cut"
            k_ = norm_value(new)
            if k_ in new_vals:                          # two old labels -> one new label
                new_vals[k_]["evidence"] += m["evidence"]
                new_vals[k_]["old_labels"].append(old)
                how += " (merged with an identical label)"
            else:
                new_vals[k_] = {"value": new, "evidence": list(m["evidence"]), "old_labels": [old],
                                "renamed": k_ != norm_value(old)}
            label_map.append({"attribute": c0["name"], "old_label": old, "new_label": new,
                              "how": how})
        for k_, m in member.items():                    # verified values the reply left out
            if k_ not in seen_old:
                folded_by_model = any(norm_value(x) == k_ for x in (a.get("folded") or []))
                as_other_old.append(m["label"])
                label_map.append({"attribute": c0["name"], "old_label": m["label"],
                                  "new_label": "other",
                                  "how": "folded into other by P4" if folded_by_model
                                  else "not returned by P4 -> other"})
        # keep the original value order, so an attribute whose labels did not change
        # renders a P5 prompt identical to run 2's (the per-call shuffle starts from it)
        order = {k_: n_ for n_, k_ in enumerate(member)}
        values = sorted(new_vals.values(),
                        key=lambda v: min(order.get(norm_value(o), 99) for o in v["old_labels"]))
        if len(values) > max_values:                    # value cap, most evidence first
            values.sort(key=lambda v: -len({e["alias"] for e in v["evidence"]}))
            for v in values[max_values:]:
                for lm in label_map:
                    if lm["attribute"] == c0["name"] and lm["new_label"] == v["value"]:
                        lm["how"] += "; folded into other (value cap)"
                        lm["new_label"] = "other"
                as_other_old += v["old_labels"]
            values = sorted(values[:max_values],
                            key=lambda v: min(order.get(norm_value(o), 99) for o in v["old_labels"]))
        prompt_values = [v["value"] for v in values] + ([NONE_LABEL] if as_other_old else [])
        entry = {
            # single-member clusters keep their name, question and gate, so that run-2 and
            # run-3 attributes can be compared one to one
            "name": c0["name"] if single else str(a["name"]).strip(),
            "question": c0["question"] if single else str(a.get("question") or c0["question"]),
            "gate": c0["gate"] if single else (a.get("gate") or "all"),
            "values": [{"value": v["value"], "evidence": v["evidence"], "renamed": v["renamed"],
                        "old_labels": v["old_labels"]} for v in values]
                      + ([{"value": NONE_LABEL, "evidence": [], "renamed": True,
                           "old_labels": as_other_old}] if as_other_old else []),
            "values_as_other": [NONE_LABEL] if as_other_old else [],
            "prompt_values": prompt_values,
            "hypothesis": c0.get("hypothesis"),
            "merged_from": [cands[i]["display_name"] for i in ix],
            "merged_from_cids": [cands[i]["cid"] for i in ix],
            "merged_from_model_reported": a["merged_from"],
            "model_changed": {"name": norm_value(a.get("name")) != norm_value(c0["name"]),
                              "question": norm_value(a.get("question") or "") != norm_value(c0["question"])}
                             if single else None,
            "removed_values": [], "folded": [str(x) for x in (a.get("folded") or [])],
            "rounds": sorted({str(cands[i]["round"]) for i in ix}),
        }
        if len(values) < run.cfg["verify"]["min_values"]:
            entry["status"] = "dropped"
            entry["drop_reason"] = (f"{len(values)} meaningful value(s) after relabelling "
                                    f"(other-type values count as other)")
        else:
            entry["status"] = "kept"
        merged.append(entry)
    return {"merged": merged, "label_map": label_map, "limit_log": limit_log, "raw": raw}


def print_label_map(label_map: list[dict]) -> None:
    print("\n=== old_label -> new_label (step 4) ===", flush=True)
    cur = None
    for r in label_map:
        if r["attribute"] != cur:
            cur = r["attribute"]
            print(f"\n[{cur}]")
        print(f"  {r['old_label']!r:70.70s} -> {r['new_label']!r}   ({r['how']})")
    print("", flush=True)


def _round_novelty(run: Run, model_name: str) -> list[dict]:
    """For every 3b candidate: highest cosine of "name. question" to any candidate of an
    EARLIER round. A numeric aid for judging new vs reworded; not a decision rule."""
    raw = read_json(run.path("candidates_raw.json"))["candidates"]
    if len(raw) < 2:
        return []
    emb, _ = _embed([f"{c['name']}. {c['question']}" for c in raw], model_name)
    out = []
    for i, c in enumerate(raw):
        prev = [j for j, o in enumerate(raw) if isinstance(o["round"], int)
                and isinstance(c["round"], int) and o["round"] < c["round"]]
        if not prev:
            out.append({"cid": c["cid"], "round": c["round"], "max_cos_prev": None,
                        "nearest_prev": None})
            continue
        j = max(prev, key=lambda j: float(emb[i] @ emb[j]))
        out.append({"cid": c["cid"], "round": c["round"],
                    "max_cos_prev": float(emb[i] @ emb[j]), "nearest_prev": raw[j]["cid"]})
    return out


# ---------------------------------------------------------------------------
# Run 4: pick each attribute's label set from an earlier run (merge.pick_labels_from)
# ---------------------------------------------------------------------------

def _resolve_run(run: Run, d: str):
    from pathlib import Path as _P
    p = _P(d)
    return p if p.is_absolute() else run.dir.parent.parent / d


def pick_labels(run: Run) -> None:
    """No model call. For every verified attribute take the value labels of the run named in
    merge.pick_labels_from, then apply the run-3 other-type rule. A label that is not
    other-type is copied byte for byte, so its P5 prompt is the earlier run's prompt."""
    mc = run.cfg["merge"]
    src = mc["pick_labels_from"]                       # {attribute name: run dir}
    ver = read_json(run.path("candidates_verified.json"))["attributes"]
    by_run = {}
    for d in set(src.values()):
        mg = read_json(_resolve_run(run, d) / "candidates_merged.json")
        by_run[d] = {a["name"]: a for a in mg["attributes"] + mg.get("dropped", [])}
    missing = [c["name"] for c in ver if c["name"] not in src]
    extra = [n for n in src if n not in {c["name"] for c in ver}]
    if missing or extra:
        die(f"pick_labels_from does not match the verified attributes: missing {missing}, "
            f"unknown {extra}")
    out_attrs, dropped, label_log = [], [], []
    for c in ver:
        d = src[c["name"]]
        a = by_run[d].get(c["name"])
        if a is None:
            die(f"{c['name']} not found in {d}/candidates_merged.json")
        vals, as_other_old, seen = [], [], set()
        for v in a["values"]:
            lab = v["value"]
            if lab == NONE_LABEL or is_other_type(lab):
                as_other_old += v.get("old_labels") or [lab]
                if NONE_LABEL not in seen:            # one "none of these", at the position of
                    seen.add(NONE_LABEL)              # the first other-type value
                    vals.append({"value": NONE_LABEL, "evidence": [], "old_labels": [],
                                 "renamed": True})
                label_log.append({"attribute": c["name"], "source": d, "old_label": lab,
                                  "new_label": NONE_LABEL,
                                  "how": "already 'none of these' in source" if lab == NONE_LABEL
                                  else "other-type -> none of these"})
                continue
            vals.append({**v})
            label_log.append({"attribute": c["name"], "source": d, "old_label": lab,
                              "new_label": lab, "how": "copied unchanged"})
        for v in vals:
            if v["value"] == NONE_LABEL:
                v["old_labels"] = as_other_old
        meaningful = [v for v in vals if v["value"] != NONE_LABEL]
        entry = {"name": a["name"], "question": a["question"], "gate": a["gate"],
                 "values": vals, "values_as_other": [NONE_LABEL] if as_other_old else [],
                 "prompt_values": [v["value"] for v in vals],
                 "hypothesis": a.get("hypothesis"), "merged_from": a.get("merged_from"),
                 "merged_from_cids": a.get("merged_from_cids"), "rounds": a.get("rounds"),
                 "label_source": d, "became_none_of_these": as_other_old,
                 "source_status": a.get("status", "kept"), "removed_values": [], "folded": []}
        if len(meaningful) < run.cfg["verify"]["min_values"]:
            entry["status"], entry["drop_reason"] = "dropped", \
                f"{len(meaningful)} meaningful value(s) after the other-type rule"
            dropped.append(entry)
        else:
            entry["status"] = "kept"
            out_attrs.append(entry)
    out = {"mode": "pick_labels_from", "sources": src, "n_input": len(ver),
           "attributes": out_attrs, "dropped": dropped, "label_map": label_log,
           "label_limits": None, "duplicate_links": [], "clusters": [],
           "pairwise_cosine_top": [], "embedding": {}, "raw_response": None}
    write_json(run.path("candidates_merged.json"), out)
    write_meta(run, run.path("candidates_merged.json"), "4", mode="pick_labels_from",
               n_attributes=len(out_attrs), api_calls=0)
    log(f"4: labels picked for {len(ver)} attributes "
        f"({sum(1 for v in src.values() if v == list(src.values())[0])} from "
        f"{list(src.values())[0]}, the rest from the other run); {len(dropped)} dropped")
    print("\n=== label source per attribute (step 4) ===")
    for e in out_attrs + dropped:
        print(f"  {e['name']:28s} {e['label_source']}  values: {[v['value'] for v in e['values']]}"
              + (f"  none-of-these <- {e['became_none_of_these']}" if e['became_none_of_these'] else ""))
    print("", flush=True)


def run(run: Run) -> None:
    mc = run.cfg["merge"]
    if mc.get("pick_labels_from"):
        return pick_labels(run)
    ver = read_json(run.path("candidates_verified.json"))
    cands = ver["attributes"]
    if not cands:
        die("no verified candidates to merge")
    n = len(cands)
    texts = [f"{c['name']}. {c['question']}" for c in cands]
    emb, emb_info = _embed(texts, mc["embedding_model"])
    sim = emb @ emb.T
    log(f"4: embedded {n} candidates with {emb_info}")

    if n > 1:
        from sklearn.cluster import AgglomerativeClustering
        cl = AgglomerativeClustering(n_clusters=None, metric="cosine", linkage=mc["linkage"],
                                     distance_threshold=1 - mc["cosine_threshold"])
        lab = cl.fit_predict(emb)
    else:
        lab = np.zeros(1, dtype=int)

    uf = _UF(n)
    groups_emb = defaultdict(list)
    for i, l in enumerate(lab):
        groups_emb[int(l)].append(i)
    for idx in groups_emb.values():
        for i in idx[1:]:
            uf.union(i, idx[0])
    cid_idx = {c["cid"]: i for i, c in enumerate(cands)}
    dup_links = []
    for i, c in enumerate(cands):
        t = c.get("duplicate_of_cid")
        if t:
            if t in cid_idx:
                uf.union(i, cid_idx[t])
                dup_links.append([c["cid"], t, "applied"])
            else:
                dup_links.append([c["cid"], t, "target did not survive 3d - stands alone"])
    clusters = defaultdict(list)
    for i in range(n):
        clusters[uf.find(i)].append(i)
    clusters = sorted(clusters.values(), key=lambda ix: min(ix))

    multi = [ix for ix in clusters if len(ix) > 1]
    merged: list[dict] = []
    cluster_log = []
    raw = None
    limit_log: dict = {}
    label_map: list[dict] = []
    if mc.get("apply_limits_to_all"):
        rr = relabel_all(run, cands, clusters, sim)
        merged, label_map, limit_log, raw = rr["merged"], rr["label_map"], rr["limit_log"], rr["raw"]
        multi_done = True
    else:
        multi_done = False
    if multi and not multi_done:
        template, version = load_prompt(run, "P4")
        groups = [{"group": g + 1, "candidates": [_verified_view(cands[i]) for i in ix]}
                  for g, ix in enumerate(multi)]
        p = render(template, groups=json.dumps(groups, indent=1, ensure_ascii=False))

        def validator(obj):
            atts = obj.get("attributes") if isinstance(obj, dict) else obj
            if not isinstance(atts, list) or len(atts) != len(multi):
                raise ValueError(f"expected {len(multi)} merged attributes, got "
                                 f"{len(atts) if isinstance(atts, list) else type(atts)}")
            for a in atts:
                if not isinstance(a, dict) or not a.get("name") or not a.get("question") \
                        or not isinstance(a.get("values"), list) \
                        or not isinstance(a.get("merged_from"), list):
                    raise ValueError(f"malformed merged attribute {str(a)[:150]}")
            return atts

        strong = LLM(run, "strong")
        raw = strong.complete_json(p, step="4", prompt_version=version, item="merge",
                                   validator=validator)
        lim_words, lim_vals = mc.get("label_max_words"), mc.get("max_values")
        limit_log = {"enforced": bool(lim_words)}
        if lim_words:
            viol = [x for a in raw for x in label_violations(a, lim_words, lim_vals)]
            limit_log["violations_first_reply"] = viol
            n_retry = mc.get("limit_violation_retries", 1)
            for k in range(n_retry):
                if not viol:
                    break
                log(f"4: merge reply violates the label limits ({len(viol)}); retry {k + 1}")
                raw = strong.complete_json(p, step="4", prompt_version=version,
                                           item="merge", validator=validator,
                                           salt_prefix=f"limits{k + 1}")
                viol = [x for a in raw for x in label_violations(a, lim_words, lim_vals)]
                limit_log[f"violations_retry{k + 1}"] = viol
            limit_log["mechanical_fix_needed"] = bool(viol)
        # match each reply to a group by merged_from overlap
        used = set()
        for g, ix in enumerate(multi):
            names = {norm_value(cands[i]["display_name"]) for i in ix} | \
                    {norm_value(cands[i]["name"]) for i in ix}
            best, best_ov = None, -1
            for k, a in enumerate(raw):
                if k in used:
                    continue
                ov = len(names & {norm_value(x) for x in a["merged_from"]})
                if ov > best_ov:
                    best, best_ov = k, ov
            if best_ov <= 0:
                die(f"merge reply has no attribute matching group {g + 1}")
            used.add(best)
            a = raw[best]
            # evidence pool of the cluster: verified evidence only
            pool = {}
            for i in ix:
                for v in cands[i]["values"]:
                    if v["status"] != "kept":
                        continue
                    for e in v["evidence"]:
                        if e.get("confirmed"):
                            pool[e["alias"]] = e["prompt_id"]
            member_vals = {norm_value(v["value"]) for i in ix for v in cands[i]["values"]
                           if v["status"] == "kept"}
            values, removed = [], []
            for v in a["values"]:
                label = str(v.get("value", "")).strip()
                if norm_value(label) == "other":
                    removed.append({"value": label, "reason": "explicit 'other'"})
                    continue
                ev = [e for e in (v.get("evidence") or []) if isinstance(e, dict)]
                ok_ev = [{"alias": str(e.get("prompt_id")).strip(),
                          "prompt_id": pool[str(e.get("prompt_id")).strip()],
                          "quote": e.get("quote")} for e in ev
                         if str(e.get("prompt_id")).strip() in pool]
                if not ok_ev and norm_value(label) in member_vals:
                    # the model kept a member's label but did not copy its evidence:
                    # take that member value's verified evidence
                    ok_ev = [{"alias": e["alias"], "prompt_id": e["prompt_id"],
                              "quote": e["quote"], "from_member": True}
                             for i in ix for mv in cands[i]["values"]
                             if mv["status"] == "kept" and norm_value(mv["value"]) == norm_value(label)
                             for e in mv["evidence"] if e.get("confirmed")]
                if not ok_ev:
                    removed.append({"value": label, "reason": "no evidence from the cluster's "
                                                              "verified evidence"})
                    continue
                values.append({"value": label, "evidence": ok_ev,
                               "renamed": norm_value(label) not in member_vals})
            folded = [str(x) for x in (a.get("folded") or [])]
            fixed = []
            if lim_words and limit_log.get("mechanical_fix_needed"):
                merged_vals: dict[str, dict] = {}
                for v in values:
                    lab = v["value"]
                    if "," in lab or _OR.search(lab) or len(lab.split()) > lim_words:
                        new_lab = truncate_label(lab, lim_words)
                        fixed.append({"from": lab, "to": new_lab})
                        v = {**v, "value": new_lab, "original_label": lab,
                             "renamed": norm_value(new_lab) not in member_vals}
                    k_ = norm_value(v["value"])
                    if k_ in merged_vals:          # truncation made two labels identical
                        merged_vals[k_]["evidence"] += v["evidence"]
                    else:
                        merged_vals[k_] = v
                values = list(merged_vals.values())
                if len(values) > lim_vals:
                    values.sort(key=lambda v: -len({e["alias"] for e in v["evidence"]}))
                    for v in values[lim_vals:]:
                        folded.append(v["value"])
                        fixed.append({"from": v["value"], "to": "other (value cap)"})
                    values = values[:lim_vals]
            gate = a.get("gate")
            gate = "all" if gate is None or norm_value(gate) in ("all", "") else str(gate)
            entry = {"name": str(a["name"]).strip(), "question": str(a["question"]).strip(),
                     "gate": gate, "values": values, "hypothesis": a.get("hypothesis"),
                     "merged_from": [cands[i]["display_name"] for i in ix],
                     "merged_from_cids": [cands[i]["cid"] for i in ix],
                     "merged_from_model_reported": a["merged_from"],
                     "removed_values": removed, "folded": folded,
                     "mechanical_fixes": fixed,
                     "rounds": sorted({str(cands[i]["round"]) for i in ix})}
            if len(values) < run.cfg["verify"]["min_values"]:
                entry["status"] = "dropped"
                entry["drop_reason"] = f"{len(values)} value(s) left after merge"
            else:
                entry["status"] = "kept"
            merged.append(entry)
            cluster_log.append({"members": entry["merged_from_cids"],
                                "result": entry["name"], "status": entry["status"],
                                "min_pairwise_cosine": float(min(sim[i, j] for i in ix
                                                                 for j in ix if i < j))})
    for ix in clusters:
        if len(ix) == 1 and not multi_done:
            c = cands[ix[0]]
            values = [{"value": v["value"],
                       "evidence": [{"alias": e["alias"], "prompt_id": e["prompt_id"],
                                     "quote": e["quote"]} for e in v["evidence"]
                                    if e.get("confirmed")], "renamed": False}
                      for v in c["values"] if v["status"] == "kept"]
            merged.append({"name": c["name"], "question": c["question"], "gate": c["gate"],
                           "values": values, "hypothesis": c.get("hypothesis"),
                           "merged_from": [c["display_name"]], "merged_from_cids": [c["cid"]],
                           "removed_values": [], "rounds": [str(c["round"])],
                           "status": "kept"})
    # unique names
    seen = defaultdict(int)
    for a in merged:
        seen[norm_value(a["name"])] += 1
        if seen[norm_value(a["name"])] > 1:
            a["name"] = f"{a['name']} ({seen[norm_value(a['name'])]})"

    kept = [a for a in merged if a["status"] == "kept"]
    if mc.get("label_max_words") and not multi_done:
        for a in merged:
            if len(a["merged_from_cids"]) == 1:
                a["label_limit_violations"] = label_violations(
                    a, mc["label_max_words"], mc["max_values"])
    novelty = _round_novelty(run, mc["embedding_model"])
    out = {"embedding": emb_info, "cosine_threshold": mc["cosine_threshold"],
           "linkage": mc["linkage"], "n_input": n, "n_clusters": len(clusters),
           "n_multi_member_clusters": len(multi), "duplicate_links": dup_links,
           "clusters": cluster_log,
           "pairwise_cosine_top": sorted(
               [[cands[i]["cid"], cands[j]["cid"], float(sim[i, j])]
                for i in range(n) for j in range(i + 1, n)], key=lambda x: -x[2])[:30],
           "attributes": kept, "dropped": [a for a in merged if a["status"] != "kept"],
           "label_limits": limit_log if (multi or multi_done) else None,
           "label_map": label_map,
           "round_novelty": novelty,
           "raw_response": raw}
    write_json(run.path("candidates_merged.json"), out)
    write_meta(run, run.path("candidates_merged.json"), "4", embedding=emb_info,
               n_attributes=len(kept))
    log(f"4: {n} candidates -> {len(clusters)} clusters ({len(multi)} multi-member) -> "
        f"{len(kept)} attributes"
        + (f" ({len(merged) - len(kept)} dropped after relabelling: "
           f"{[a['name'] for a in merged if a['status'] != 'kept']})" if multi_done else ""))
    if label_map:
        print_label_map(label_map)
