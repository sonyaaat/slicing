"""Step 5 of the v5 corpus run - sample annotation and curation.

Sample: 300 discovery messages stratified by theme (equal allocation, ~43 per theme), seed 42.
Three annotations of every (message, attribute):
  primary    qwen3.6-35b-a3b, seed 42
  repeat     qwen3.6-35b-a3b, seed 43 (other value order, other API seed) -> reliability
  second     qwen3.8-27b, seed 42 -> cross-model agreement (reported, not a filter)

Filters, in curation.filter_order (coverage -> support -> reliability -> redundancy ->
none_artifact). Thresholds from run_config:
  coverage   share of the sample with a listed value, other or not_stated (not_applicable,
             unknown, parse_error do not count): corpus >= 0.7 else dropped; any theme < 0.5
             -> thematic pool (not dropped)
  support    values with < 15 items in the sample -> other; < 2 values left -> dropped.
             not_stated is a value (spec step 6: it is a fact about the message)
  reliability agreement primary vs repeat (after the value map) >= 0.8
  redundancy Cramer's V > 0.5 on items where both are covered -> drop the lower coverage
  none_artifact a value whose items are > 0.8 physician-category "none" -> other
Curation never looks at a score.
"""

from __future__ import annotations

import math
from collections import Counter

import numpy as np
import pandas as pd

from common import NA, OTHER, PARSE_ERROR, UNKNOWN, Run, die, log, read_json, slug, write_json, write_meta
from step5_curate import cramers_v, norm_entropy
from v5_annotate import NONE_LABEL, NOT_STATED, annotate_one
from v5_data import discovery_frame, theme_sample
from v5_infra import V5LLM, decide, run_jobs

UNCOVERED = (NA, UNKNOWN, PARSE_ERROR)
COLS = ["prompt_id", "attribute", "value", "evidence_span", "unknown_reason", "value_raw",
        "flags", "error", "seed", "model"]


def annotate_grid(run: Run, llm: V5LLM, attrs: list[dict], pids: list[str], text: dict,
                  seed: int, step: str, add_total: bool = True) -> pd.DataFrame:
    jobs = [(a, pid) for a in attrs for pid in pids]
    log(f"{step}: {len(jobs)} calls ({len(attrs)} attributes x {len(pids)} items), {llm.model}")

    def one(job):
        a, pid = job
        return annotate_one(llm, run, {"name": a["name"], "question": a["question"],
                                       "values": a["prompt_values"]},
                            pid, text[pid], seed=seed, step=step)

    res = run_jobs(run, step, jobs, lambda j: f"{j[0]['name']}|{j[1]}|{seed}|{llm.model}",
                   one, llm.n_slots, f"{step} annotate", add_total=add_total)
    df = pd.DataFrame(res)
    for c in COLS:
        if c not in df.columns:
            df[c] = None
    return df[COLS]


def value_map(a: dict) -> dict:
    """Prompt label -> stored label. Absence labels are stored as not_stated by P5 already;
    'none of these' counts as other."""
    m = {v: v for v in a["prompt_values"] if v not in a.get("absence_values", [])}
    for v in a.get("values_as_other", []):
        m[v] = OTHER
    m[NOT_STATED] = NOT_STATED
    return m


def mapped(series: pd.Series, vmap: dict) -> pd.Series:
    return series.map(lambda v: v if v in UNCOVERED or v == OTHER else vmap.get(v, v))


def run(run: Run, limit: int | None = None) -> None:
    acfg, ccfg = run.cfg["annotation"], run.cfg["curation"]
    if ccfg["filter_order"] != ["coverage", "support", "reliability", "redundancy", "none_artifact"]:
        die(f"unsupported filter order {ccfg['filter_order']}")
    merged = read_json(run.path("candidates_merged.json"))["attributes"]
    # manual removals recorded in the run's config (curation.removed_before_annotation)
    removed = {x["name"]: x["reason"] for x in ccfg.get("removed_before_annotation", [])}
    unknown = set(removed) - {a["name"] for a in merged}
    if unknown:
        die(f"curation.removed_before_annotation names unknown attributes {sorted(unknown)}")
    for n, why in removed.items():
        decide(run, "5", f"'{n}' removed before annotation (manual decision)", why)
    merged = [a for a in merged if a["name"] not in removed]
    if not merged:
        die("no merged attributes")
    d = discovery_frame(run)
    text = dict(zip(d.prompt_id, d.user_text))
    theme = dict(zip(d.prompt_id, d.theme))
    phys = dict(zip(d.prompt_id, d.physician_category))
    sample = theme_sample(d, acfg["sample_n"], acfg["sample_seed"])
    if limit:
        sample = sample[:limit]
    write_json(run.path("sample_ids.json"), {"ids": sample, "seed": acfg["sample_seed"],
                                             "by_theme": dict(Counter(theme[p] for p in sample))})
    llm = V5LLM(run, "annotation")
    llm_x = V5LLM(run, "annotation", model_override=acfg["second_model"])
    from v5_infra import PROGRESS
    PROGRESS.add_total(3 * len(merged) * len(sample))     # all three grids, for the ETA
    ann = annotate_grid(run, llm, merged, sample, text, acfg["seed"], "5", add_total=False)
    ann.to_csv(run.path("annotations_sample.csv"), index=False)
    rep = annotate_grid(run, llm, merged, sample, text, acfg["reliability_seed"], "5rel", add_total=False)
    rep.to_csv(run.path("annotations_reliability.csv"), index=False)
    xm = annotate_grid(run, llm_x, merged, sample, text, acfg["seed"], "5x", add_total=False)
    xm.to_csv(run.path("annotations_crossmodel.csv"), index=False)
    for f, mdl, sd in (("annotations_sample.csv", llm.model, acfg["seed"]),
                       ("annotations_reliability.csv", llm.model, acfg["reliability_seed"]),
                       ("annotations_crossmodel.csv", llm_x.model, acfg["seed"])):
        write_meta(run, run.path(f), "5", model=mdl, seed=sd, n_items=len(sample),
                   n_attributes=len(merged))

    wide = ann.pivot(index="prompt_id", columns="attribute", values="value")
    wrel = rep.pivot(index="prompt_id", columns="attribute", values="value")
    wx = xm.pivot(index="prompt_id", columns="attribute", values="value")
    themes = sorted(set(theme[p] for p in sample))
    m: dict[str, dict] = {}
    vmaps = {a["name"]: value_map(a) for a in merged}
    for a in merged:
        n = a["name"]
        col = wide[n]
        cov = (~col.isin(UNCOVERED)).mean()
        covt = {t: float((~col[[p for p in col.index if theme[p] == t]].isin(UNCOVERED)).mean())
                for t in themes}
        m[n] = {"attribute": n, "column": slug(n), "question": a["question"],
                "values": " | ".join(a["prompt_values"]),
                "coverage": float(cov), **{f"coverage_{t}": covt[t] for t in themes},
                "min_theme_coverage": min(covt.values()),
                "min_theme_coverage_theme": min(covt, key=covt.get),
                "share_not_applicable": float((col == NA).mean()),
                "share_not_stated": float((col == NOT_STATED).mean()),
                "share_unknown": float((col == UNKNOWN).mean()),
                "n_parse_error": int((col == PARSE_ERROR).sum()),
                "status": "kept", "drop_reason": None, "dropped_at_filter": None}

    def drop(n, f, reason, status="dropped"):
        m[n]["status"], m[n]["drop_reason"], m[n]["dropped_at_filter"] = status, reason, f
        if status == "thematic_pool":
            decide(run, "5", f"'{n}' -> thematic pool", reason)

    alive = lambda: [n for n in m if m[n]["status"] == "kept"]  # noqa: E731

    # coverage
    for n in alive():
        if m[n]["coverage"] < ccfg["min_coverage_corpus"]:
            drop(n, "coverage", f"corpus coverage {m[n]['coverage']:.3f} < {ccfg['min_coverage_corpus']}")
        elif m[n]["min_theme_coverage"] < ccfg["min_coverage_theme"]:
            low = {t: round(m[n][f"coverage_{t}"], 3) for t in themes
                   if m[n][f"coverage_{t}"] < ccfg["min_coverage_theme"]}
            drop(n, "coverage", f"theme coverage < {ccfg['min_coverage_theme']} in {low}",
                 status="thematic_pool")
    # support (computed for all, for a complete table)
    for a in merged:
        n = a["name"]
        col = mapped(wide[n], vmaps[n])
        cnt = Counter(col[~col.isin(UNCOVERED)])
        small = [v for v in set(vmaps[n].values()) if v != OTHER and cnt.get(v, 0) < ccfg["min_support_sample"]]
        for k, v in list(vmaps[n].items()):
            if v in small:
                vmaps[n][k] = OTHER
        meaningful = sorted(v for v in set(vmaps[n].values()) if v != OTHER)
        m[n].update(folded_support=small, n_values_after_support=len(meaningful),
                    min_support=min((cnt.get(v, 0) for v in meaningful), default=0))
        if m[n]["status"] == "kept" and len(meaningful) < 2:
            drop(n, "support", f"{len(meaningful)} value(s) with >= {ccfg['min_support_sample']} "
                               f"items (folded: {small})")
    # reliability and cross-model agreement for all
    for a in merged:
        n = a["name"]
        x = mapped(wide.loc[wrel.index, n], vmaps[n]); y = mapped(wrel[n], vmaps[n])
        m[n]["reliability"] = float((x == y).mean())
        x2 = mapped(wide.loc[wx.index, n], vmaps[n]); y2 = mapped(wx[n], vmaps[n])
        m[n]["cross_model_agreement"] = float((x2 == y2).mean())
    for n in alive():
        if m[n]["reliability"] < ccfg["min_reliability"]:
            drop(n, "reliability", f"reliability {m[n]['reliability']:.3f} < {ccfg['min_reliability']}")
    # redundancy
    entered = alive()
    pairs = []
    for i, x in enumerate(entered):
        for y in entered[i + 1:]:
            vx, vy = mapped(wide[x], vmaps[x]), mapped(wide[y], vmaps[y])
            ok = ~vx.isin(UNCOVERED) & ~vy.isin(UNCOVERED)
            v = cramers_v(vx[ok], vy[ok]) if ok.sum() >= 10 else float("nan")
            pairs.append((x, y, v, int(ok.sum())))
    write_json(run.path("cramers_v_pairs.json"), [list(p) for p in pairs])
    for n in m:
        mine = [(p[1] if p[0] == n else p[0], p[2]) for p in pairs if n in p[:2] and not math.isnan(p[2])]
        if mine:
            o, v = max(mine, key=lambda t: t[1])
            m[n]["max_cramers_v"], m[n]["max_cramers_v_with"] = v, o
        else:
            m[n]["max_cramers_v"], m[n]["max_cramers_v_with"] = float("nan"), None
    for x, y, v, nb in sorted(pairs, key=lambda p: -(p[2] if not math.isnan(p[2]) else -1)):
        if math.isnan(v) or v < ccfg["max_cramers_v"] or m[x]["status"] != "kept" or m[y]["status"] != "kept":
            continue
        kx, ky = (m[x]["coverage"], m[x]["reliability"], x), (m[y]["coverage"], m[y]["reliability"], y)
        loser, winner = (y, x) if kx > ky else (x, y)
        drop(loser, "redundancy", f"Cramer's V {v:.3f} >= {ccfg['max_cramers_v']} with '{winner}' "
                                  f"(n={nb}); kept the one with higher coverage")
    # none artifact
    for a in merged:
        n = a["name"]
        col = mapped(wide[n], vmaps[n])
        art = []
        for v in sorted(set(vmaps[n].values()) - {OTHER}):
            ids = col[col == v].index
            share = float(np.mean([phys[p] == "none" for p in ids])) if len(ids) else 0.0
            if share > ccfg["none_overlap_max"]:
                art.append([v, round(share, 3), len(ids)])
        m[n]["none_artifact_values"] = art
        if m[n]["status"] != "kept" or not art:
            continue
        for k, v in list(vmaps[n].items()):
            if v in [x[0] for x in art]:
                vmaps[n][k] = OTHER
        decide(run, "5", f"'{n}': values {[x[0] for x in art]} folded into other",
               f"> {ccfg['none_overlap_max']} of their items have physician category 'none'")
        if len(set(vmaps[n].values()) - {OTHER}) < 2:
            drop(n, "none_artifact", "fewer than 2 values after removing none-artifact values")
    for a in merged:
        n = a["name"]
        col = mapped(wide[n], vmaps[n])
        cnt = Counter(col[~col.isin(UNCOVERED)])
        m[n]["entropy"] = norm_entropy(cnt)
        m[n]["sliceability"] = (m[n]["coverage"] + m[n]["entropy"] + m[n]["reliability"]) / 3
        m[n]["value_counts_sample"] = dict(cnt)
        m[n]["value_map"] = vmaps[n]
    tab = pd.DataFrame([m[n] for n in m])
    tab.to_csv(run.path("attribute_metrics.csv"), index=False)
    write_meta(run, run.path("attribute_metrics.csv"), "5", thresholds=ccfg)

    by = {a["name"]: a for a in merged}
    final = []
    for n in alive():
        a = by[n]
        final.append({"name": n, "column": slug(n), "question": a["question"],
                      "prompt_values": a["prompt_values"], "absence_values": a.get("absence_values", []),
                      "values_as_other": a.get("values_as_other", []),
                      "values": sorted(set(vmaps[n].values()) - {OTHER}) + [OTHER],
                      "value_map": vmaps[n], "merged_from": a.get("merged_from"),
                      "metrics": {k: m[n][k] for k in ("coverage", "min_theme_coverage", "reliability",
                                                       "cross_model_agreement", "max_cramers_v",
                                                       "entropy", "sliceability")}})
    if Counter(f["column"] for f in final).most_common(1)[0][1] > 1 if final else False:
        die("column name collision among final attributes")
    write_json(run.path("attributes_final.json"),
               {"attributes": final, "sample_n": len(sample), "annotation_model": llm.model,
                "second_model": llm_x.model, "seed": acfg["seed"],
                "reliability_seed": acfg["reliability_seed"]})
    write_meta(run, run.path("attributes_final.json"), "5", n_final=len(final))
    pool = read_json(run.path("thematic_pool.json"))
    pool["attributes"] = [x for x in pool["attributes"] if x.get("source") != "5"] + [
        {"name": n, "question": by[n]["question"], "values": by[n]["prompt_values"], "source": "5",
         "reason": m[n]["drop_reason"],
         "coverage_by_theme": {t: round(m[n][f"coverage_{t}"], 3) for t in themes}}
        for n in m if m[n]["status"] == "thematic_pool"]
    write_json(run.path("thematic_pool.json"), pool)
    log(f"5: {len(merged)} in, {len(final)} final; "
        f"{dict(Counter((m[n]['status'], m[n]['dropped_at_filter']) for n in m))}")
    if not final:
        die("step 5 left no universal attribute - the run stops here (this is a result)")
