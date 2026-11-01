"""Step 4 of the v5 corpus run - merge and labels.

1. bge-m3 embedding of "name. question" of every universal verified attribute; complete-
   linkage clustering at cosine >= 0.8; the critic's duplicate links are unioned in.
2. One strong-model call (P4 v5) for all clusters, singletons included, so every label
   with a comma or "or" is rewritten in the same call.
3. The v5 label rule is enforced in code after the call:
   * an old label without a comma and without "or" is kept verbatim, whatever the reply says;
   * an old label with a comma or "or" takes the reply's new label; if that still breaks
     the limits after one retry of the whole call, it is cut mechanically (first clause,
     5 words);
   * "none of the listed" forms become "none of these" (treated as other);
   * "other: <named group>" becomes "<named group>";
   * a verified value the reply leaves out keeps its own label (rule above);
   * at most 5 concrete values (absence labels and "none of these" not counted); extra
     values with the least verified evidence are folded into "none of these".
   An attribute with fewer than 2 values left is dropped.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict

import numpy as np

from common import Run, die, load_prompt, log, norm_value, read_json, render, write_json, write_meta
from step4_merge import _UF, _embed, _norm_reply_values, _verified_view, truncate_label
from v5_annotate import NONE_LABEL, is_absence_label
from v5_infra import PROGRESS, V5LLM, decide

_OR = re.compile(r"\bor\b", re.I)
_NONE_FORMS = {"none of these", "none", "neither", "none of the above", "none of the listed",
               "none listed", "other"}


def needs_rewrite(label: str) -> bool:
    return "," in label or bool(_OR.search(label))


def breaks_limits(label: str, max_words: int) -> bool:
    return needs_rewrite(label) or len(label.split()) > max_words


def is_none_type(label: str) -> bool:
    n = norm_value(label)
    return n in _NONE_FORMS or n.startswith("none of")


def named_other(label: str) -> str | None:
    m = re.match(r"^\s*other\s*[:\-–—(]\s*(.+?)\)?\s*$", label, re.I)
    return m.group(1).strip() if m else None


def run(run: Run) -> None:
    mc = run.cfg["merge"]
    max_words, max_values = mc["label_max_words"], mc["max_values"]
    cands = read_json(run.path("candidates_verified.json"))["attributes"]
    if not cands:
        die("no universal verified attributes to merge")
    for c in cands:
        c.setdefault("display_name", c["name"])
    n = len(cands)
    emb, emb_info = _embed([f"{c['name']}. {c['question']}" for c in cands], mc["embedding_model"])
    sim = emb @ emb.T
    if n > 1:
        from sklearn.cluster import AgglomerativeClustering
        lab = AgglomerativeClustering(n_clusters=None, metric="cosine", linkage=mc["linkage"],
                                      distance_threshold=1 - mc["cosine_threshold"]).fit_predict(emb)
    else:
        lab = np.zeros(1, dtype=int)
    uf = _UF(n)
    first = {}
    for i, l in enumerate(lab):
        if int(l) in first:
            uf.union(i, first[int(l)])
        else:
            first[int(l)] = i
    cid_idx = {c["cid"]: i for i, c in enumerate(cands)}
    dup_links = []
    for i, c in enumerate(cands):
        t = c.get("duplicate_of_cid")
        if t:
            if t in cid_idx:
                uf.union(i, cid_idx[t]); dup_links.append([c["cid"], t, "applied"])
            else:
                dup_links.append([c["cid"], t, "target not universal after 3d - stands alone"])
    groups = defaultdict(list)
    for i in range(n):
        groups[uf.find(i)].append(i)
    clusters = sorted(groups.values(), key=min)
    log(f"4: {n} attributes -> {len(clusters)} clusters "
        f"({sum(len(x) > 1 for x in clusters)} multi-member)")

    template, version = load_prompt(run, "P4")
    payload = [{"group": g + 1, "candidates": [_verified_view(cands[i]) for i in ix]}
               for g, ix in enumerate(clusters)]
    for grp in payload:
        for cv in grp["candidates"]:
            cv.pop("gate", None); cv.pop("hypothesis", None)
    p = render(template, groups=json.dumps(payload, indent=1, ensure_ascii=False))

    def validator(obj):
        atts = obj.get("attributes") if isinstance(obj, dict) else obj
        if not isinstance(atts, list) or len(atts) != len(clusters):
            raise ValueError(f"expected {len(clusters)} attributes, got "
                             f"{len(atts) if isinstance(atts, list) else type(atts)}")
        for a in atts:
            if not isinstance(a, dict) or not a.get("name") or not isinstance(a.get("values"), list):
                raise ValueError(f"malformed attribute {str(a)[:150]}")
            if not isinstance(a.get("merged_from"), list):
                a["merged_from"] = []
            vs = _norm_reply_values(a)
            if not vs or any(not v["old"] or not v["new"] for v in vs):
                raise ValueError(f"attribute {a.get('name')!r}: a value lacks old or new label")
        return atts

    def violations(raw):
        out = []
        for a in raw:
            for v in _norm_reply_values(a):
                if needs_rewrite(v["old"]) and not is_none_type(v["new"]) \
                        and breaks_limits(v["new"], max_words):
                    out.append(f"{a['name']}: {v['new']!r}")
        return out

    strong = V5LLM(run, "strong")
    PROGRESS.add_total(1)
    raw = strong.complete_json(p, step="4", prompt_version=version, item="merge", validator=validator)
    viol = violations(raw)
    limit_log = {"violations_first_reply": viol}
    for k in range(mc["limit_violation_retries"]):
        if not viol:
            break
        decide(run, "4", f"merge call retried ({len(viol)} rewritten labels break the limits)",
               "v5: a rewritten label must be <= 5 words, no comma, no 'or'")
        raw = strong.complete_json(p, step="4", prompt_version=version, item="merge",
                                   validator=validator, salt_prefix=f"limits{k + 1}")
        viol = violations(raw)
        limit_log[f"violations_retry{k + 1}"] = viol
    PROGRESS.job_done()

    merged, label_map, used = [], [], set()
    for g, ix in enumerate(clusters):
        names = {norm_value(cands[i]["display_name"]) for i in ix} | {norm_value(cands[i]["name"]) for i in ix}
        best, best_ov = None, -1
        for k, a in enumerate(raw):
            if k in used:
                continue
            ov = len(names & {norm_value(x) for x in a["merged_from"]}) + \
                (1 if norm_value(a["name"]) in names else 0)
            if ov > best_ov:
                best, best_ov = k, ov
        if best is None or best_ov <= 0:
            # fall back to position: the reply lists groups in order
            best = g if g not in used and g < len(raw) else None
            if best is None:
                die(f"merge reply has no attribute matching group {g + 1}")
            decide(run, "4", f"group {g + 1} matched to reply attribute {g + 1} by position",
                   "no name overlap between the reply's merged_from and the group")
        used.add(best)
        a = raw[best]
        single = len(ix) == 1
        c0 = cands[ix[0]]
        member = {}                       # norm old label -> {label, n_evidence}
        for i in ix:
            for v in cands[i]["values"]:
                if v["status"] == "kept":
                    m = member.setdefault(norm_value(v["value"]), {"label": v["value"], "ev": set()})
                    m["ev"] |= {e["alias"] for e in v["evidence"] if e.get("confirmed")}
        new_vals: dict[str, dict] = {}
        none_old: list[str] = []
        seen = set()

        def put(old, new, how):
            label_map.append({"attribute": c0["name"] if single else str(a["name"]).strip(),
                              "old_label": old, "new_label": new, "how": how})
            if new == NONE_LABEL:
                none_old.append(old); return
            k_ = norm_value(new)
            if k_ in new_vals:
                new_vals[k_]["old_labels"].append(old)
                new_vals[k_]["ev"] |= member[norm_value(old)]["ev"]
            else:
                new_vals[k_] = {"value": new, "old_labels": [old], "ev": set(member[norm_value(old)]["ev"])}

        for v in _norm_reply_values(a):
            m = member.get(norm_value(v["old"]))
            if m is None:
                label_map.append({"attribute": c0["name"], "old_label": v["old"], "new_label": None,
                                  "how": "ignored: old label is not a verified value of the group"})
                continue
            old = m["label"]
            if norm_value(old) in seen:
                continue
            seen.add(norm_value(old))
            if is_none_type(old) or is_none_type(v["new"]):
                put(old, NONE_LABEL, "none-of-the-listed -> none of these")
            elif named_other(old):
                put(old, named_other(old), "'other: <group>' -> named group")
            elif not needs_rewrite(old):
                how = "copied verbatim" if v["new"] == old else \
                    f"copied verbatim (reply rewrote it to {v['new']!r}; reverted by the v5 rule)"
                put(old, old, how)
            else:
                new = v["new"]
                if named_other(new):
                    new = named_other(new)
                if breaks_limits(new, max_words):
                    new2 = truncate_label(new, max_words)
                    put(old, new2, f"rewritten by model to {new!r}, still over the limits -> mechanical cut")
                else:
                    put(old, new, "rewritten by model (comma or 'or' in old label)")
        for k_, m in member.items():
            if k_ in seen:
                continue
            old = m["label"]
            if is_none_type(old):
                put(old, NONE_LABEL, "not returned; none-of-the-listed -> none of these")
            elif named_other(old):
                put(old, named_other(old), "not returned; 'other: <group>' -> named group")
            elif needs_rewrite(old):
                put(old, truncate_label(old, max_words), "not returned; mechanical cut")
            else:
                put(old, old, "not returned by the reply; kept verbatim")
        vals = list(new_vals.values())
        concrete = [v for v in vals if not is_absence_label(v["value"])]
        if len(concrete) > max_values:
            concrete.sort(key=lambda v: -len(v["ev"]))
            for v in concrete[max_values:]:
                for o in v["old_labels"]:
                    none_old.append(o)
                    label_map.append({"attribute": c0["name"], "old_label": o, "new_label": NONE_LABEL,
                                      "how": "value cap (least verified evidence) -> none of these"})
                vals.remove(v)
        values = [{"value": v["value"], "old_labels": v["old_labels"], "n_verified_evidence": len(v["ev"])}
                  for v in vals]
        if none_old:
            values.append({"value": NONE_LABEL, "old_labels": none_old, "n_verified_evidence": 0})
        entry = {"name": c0["name"] if single else str(a["name"]).strip(),
                 "question": c0["question"] if single else str(a.get("question") or c0["question"]).strip(),
                 "values": values,
                 "prompt_values": [v["value"] for v in values],
                 "values_as_other": [NONE_LABEL] if none_old else [],
                 "absence_values": [v["value"] for v in values if is_absence_label(v["value"])],
                 "merged_from": [cands[i]["display_name"] for i in ix],
                 "merged_from_cids": [cands[i]["cid"] for i in ix],
                 "evidence_themes": sorted({t for i in ix for t in cands[i].get("evidence_themes", [])}),
                 "rounds": sorted({str(cands[i]["round"]) for i in ix}),
                 "folded_by_model": [str(x) for x in (a.get("folded") or [])]}
        meaningful = [v for v in values if v["value"] != NONE_LABEL]
        if len(meaningful) < run.cfg["verify"]["min_values"]:
            entry["status"], entry["drop_reason"] = "dropped", f"{len(meaningful)} value(s) after relabelling"
        else:
            entry["status"] = "kept"
        merged.append(entry)
    cnt = defaultdict(int)
    for e in merged:
        cnt[norm_value(e["name"])] += 1
        if cnt[norm_value(e["name"])] > 1:
            e["name"] = f"{e['name']} ({cnt[norm_value(e['name'])]})"
    for e in merged:
        if e["absence_values"]:
            decide(run, "4", f"'{e['name']}': {e['absence_values']} treated as not_stated",
                   "absence label; P5 v5 has a not_stated output for the same answer")
    kept = [e for e in merged if e["status"] == "kept"]
    write_json(run.path("candidates_merged.json"),
               {"embedding": emb_info, "cosine_threshold": mc["cosine_threshold"],
                "n_input": n, "n_clusters": len(clusters), "duplicate_links": dup_links,
                "clusters": [[cands[i]["cid"] for i in ix] for ix in clusters],
                "pairwise_cosine_top": sorted([[cands[i]["cid"], cands[j]["cid"], float(sim[i, j])]
                                               for i in range(n) for j in range(i + 1, n)],
                                              key=lambda x: -x[2])[:30],
                "attributes": kept, "dropped": [e for e in merged if e["status"] != "kept"],
                "label_map": label_map, "limit_log": limit_log, "raw_response": raw})
    write_meta(run, run.path("candidates_merged.json"), "4", model=strong.model,
               embedding=emb_info, n_attributes=len(kept))
    log(f"4: {len(kept)} attributes kept, {len(merged) - len(kept)} dropped")
