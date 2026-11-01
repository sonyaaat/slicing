"""Step 5 - annotate a 150-item discovery sample, then curate by sliceability metrics.

Annotation: P5, one attribute per call, annotation model, temperature 0, seed from
run_config. Reliability: reliability_n items of the sample re-annotated with the
reliability seed (changes the value order in the prompt and the API seed).

Curation filters, applied in this order with thresholds fixed in run_config.json:
  1 coverage    concrete values / items where the gate says yes (all items if gate=all)
  2 support     values with < min_support_sample items are folded into "other";
                < 2 meaningful values left -> drop
  3 redundancy  Cramer's V > max on items where both are concrete -> drop lower coverage
  4 reliability agreement with the recheck < min_reliability -> drop
  5 none        a value whose items are > none_overlap_max from the physician-category
                "none" group is folded into "other"; < 2 meaningful values -> drop

Curation never looks at the score.
"""

from __future__ import annotations

import math
from collections import Counter

import numpy as np
import pandas as pd

from annotate import annotate_one
from common import (NA, OTHER, PARSE_ERROR, UNKNOWN, Run, die, log, norm_value, read_json,
                    slug, write_json, write_meta)
from llm_client import LLM, run_parallel

NONCONCRETE = (UNKNOWN, NA, PARSE_ERROR)


def attr_spec(a: dict) -> dict:
    return {"name": a["name"], "question": a["question"], "gate": a["gate"],
            "values": [v["value"] for v in a["values"]]}


def annotate_grid(run: Run, llm: LLM, attrs: list[dict], pids: list[str], text: dict,
                  seed: int, step: str) -> pd.DataFrame:
    jobs = [(a, pid) for a in attrs for pid in pids]
    log(f"{step}: {len(jobs)} annotation calls ({len(attrs)} attributes x {len(pids)} items)")

    def one(job):
        a, pid = job
        return annotate_one(llm, run, attr_spec(a), pid, text[pid], seed=seed, step=step)

    res = run_parallel(one, jobs, llm.n_slots, f"{step} annotate", every=500)
    rows = []
    for (a, pid), r in zip(jobs, res):
        if isinstance(r, Exception):
            r = {"prompt_id": pid, "attribute": a["name"], "seed": seed, "gate_answer": None,
                 "value": PARSE_ERROR, "value_raw": None, "evidence_span": None,
                 "unknown_reason": None, "flags": "exception", "error": str(r)[:300]}
        rows.append(r)
    cols = ["prompt_id", "attribute", "gate_answer", "value", "evidence_span",
            "unknown_reason", "value_raw", "flags", "error", "seed"]
    return pd.DataFrame(rows)[cols]


def cramers_v(x: pd.Series, y: pd.Series) -> float:
    ct = pd.crosstab(x, y)
    if ct.shape[0] < 2 or ct.shape[1] < 2:
        return float("nan")
    from scipy.stats import chi2_contingency
    chi2 = chi2_contingency(ct, correction=False)[0]
    n = ct.values.sum()
    return float(math.sqrt(chi2 / (n * (min(ct.shape) - 1))))


def norm_entropy(counts: Counter) -> float:
    c = np.array([v for v in counts.values() if v > 0], dtype=float)
    if len(c) < 2:
        return 0.0
    p = c / c.sum()
    return float(-(p * np.log(p)).sum() / math.log(len(c)))


def run(run: Run, limit: int | None = None) -> None:
    acfg, ccfg = run.cfg["annotation"], run.cfg["curation"]
    merged = read_json(run.path("candidates_merged.json"))["attributes"]
    if not merged:
        die("no merged attributes")
    df = pd.read_csv(run.path("uc1_data.csv"))
    disc = df[df.split == "discovery"].sort_values("prompt_id").reset_index(drop=True)
    text = dict(zip(df.prompt_id, df.user_text))
    phys = dict(zip(df.prompt_id, df.physician_category))

    rng = np.random.default_rng(acfg["seed"])
    sample = sorted(rng.choice(disc.prompt_id.to_numpy(), size=acfg["sample_n"],
                               replace=False).tolist())
    rel = sorted(np.random.default_rng(acfg["seed"]).choice(
        np.array(sample), size=acfg["reliability_n"], replace=False).tolist())
    if limit is not None:
        sample, rel = sample[:limit], rel[:min(limit, len(rel))]
        rel = [p for p in rel if p in sample] or sample[:2]

    llm = LLM(run, "annotation")
    llm_rel = LLM(run, "annotation", model_override=acfg["reliability_model"])
    ann = annotate_grid(run, llm, merged, sample, text, acfg["seed"], "5")
    ann.to_csv(run.path("annotations_sample.csv"), index=False)
    write_meta(run, run.path("annotations_sample.csv"), "5", model=llm.model,
               seed=acfg["seed"], n_items=len(sample), n_attributes=len(merged))
    rec = annotate_grid(run, llm_rel, merged, rel, text, acfg["reliability_seed"], "5rel")
    rec.to_csv(run.path("annotations_reliability.csv"), index=False)
    write_meta(run, run.path("annotations_reliability.csv"), "5", model=llm_rel.model,
               seed=acfg["reliability_seed"], n_items=len(rel))
    xm = None
    if acfg.get("second_model"):
        # second annotator, same prompt and seed: reported as cross_model_agreement only
        llm_x = LLM(run, "annotation", model_override=acfg["second_model"])
        xm = annotate_grid(run, llm_x, merged, sample, text, acfg["seed"], "5x")
        xm.to_csv(run.path("annotations_crossmodel.csv"), index=False)
        write_meta(run, run.path("annotations_crossmodel.csv"), "5", model=llm_x.model,
                   seed=acfg["seed"], n_items=len(sample), note="reported only, not a filter")

    # ----------------------------------------------------------- metrics
    by_attr = {a["name"]: a for a in merged}
    wide = ann.pivot(index="prompt_id", columns="attribute", values="value")
    wide_rel = rec.pivot(index="prompt_id", columns="attribute", values="value")
    gate_yes = ann.pivot(index="prompt_id", columns="attribute", values="gate_answer")

    m: dict[str, dict] = {}
    mapping: dict[str, dict] = {}
    for a in merged:
        n = a["name"]
        col = wide[n]
        gated = norm_value(a["gate"]) != "all"
        # "Items where the gate says yes" = items that did not fail the gate, i.e. whose
        # value is not not_applicable. The model sometimes chooses a value without filling
        # gate_answer; such an item passed the gate and belongs in the denominator.
        base = col[col != NA] if gated else col
        conc = base[~base.isin(NONCONCRETE)]
        coverage = len(conc) / len(base) if len(base) else 0.0
        counts = Counter(col[~col.isin(NONCONCRETE)])
        m[n] = {"attribute": n, "column": slug(n), "question": a["question"], "gate": a["gate"],
                "values": " | ".join(v["value"] for v in a["values"]),
                "n_gate_yes": int((col != NA).sum()) if gated else None,
                "coverage": coverage,
                "n_unknown": int((col == UNKNOWN).sum()), "n_na": int((col == NA).sum()),
                "n_parse_error": int((col == PARSE_ERROR).sum()),
                "value_counts_raw": dict(counts), "status": "kept", "drop_reason": None,
                "dropped_at_filter": None}
        mapping[n] = {v["value"]: v["value"] for v in a["values"]}
        for v in a.get("values_as_other", []):   # run 3: "none of these" counts as other
            mapping[n][v] = OTHER

    def drop(n, f, reason):
        m[n]["status"], m[n]["drop_reason"], m[n]["dropped_at_filter"] = "dropped", reason, f

    alive = lambda: [n for n in m if m[n]["status"] == "kept"]  # noqa: E731

    # 1 coverage
    for n in alive():
        if m[n]["coverage"] < ccfg["min_coverage"]:
            drop(n, 1, f"coverage {m[n]['coverage']:.3f} < {ccfg['min_coverage']}")

    # 2 support (computed for every attribute so the table is complete)
    def mapped(n, series):
        return series.map(lambda v: v if v in NONCONCRETE or v == OTHER else mapping[n].get(v, v))

    for n in m:
        counts = m[n]["value_counts_raw"]
        small = [v for v in mapping[n] if mapping[n][v] == v
                 and counts.get(v, 0) < ccfg["min_support_sample"]]
        for v in small:
            mapping[n][v] = OTHER
        meaningful = [v for v in mapping[n] if mapping[n][v] == v]
        m[n]["folded_into_other_support"] = small
        m[n]["min_support"] = min((counts.get(v, 0) for v in meaningful), default=0)
        m[n]["n_meaningful_after_support"] = len(meaningful)
        if m[n]["status"] == "kept" and len(meaningful) < 2:
            drop(n, 2, f"{len(meaningful)} value(s) with support >= "
                       f"{ccfg['min_support_sample']} (folded: {small})")

    # reliability for every attribute (needed for filter 3 tie-break and filter 4)
    for n in m:
        if n not in wide_rel.columns:
            m[n]["reliability"] = float("nan"); continue
        a_ = mapped(n, wide.loc[wide_rel.index, n])
        b_ = mapped(n, wide_rel[n])
        m[n]["reliability"] = float((a_ == b_).mean())
        m[n]["reliability_n"] = int(len(b_))

    for n in m:
        m[n]["cross_model_agreement"] = float("nan")
        if xm is not None:
            wx = xm.pivot(index="prompt_id", columns="attribute", values="value")
            if n in wx.columns:
                a_ = mapped(n, wide.loc[wx.index, n])
                b_ = mapped(n, wx[n])
                m[n]["cross_model_agreement"] = float((a_ == b_).mean())

    for n in m:
        m[n].setdefault("max_cramers_v", float("nan")); m[n].setdefault("max_cramers_v_with", None)
    # Filters 3-5 run in curation.filter_order (run 4: reliability before redundancy).
    # Coverage and support always run first: every later metric uses the support fold.
    def f_redundancy():
        # 3 redundancy among attributes still alive
        entered3 = alive()
        pairs = []
        for i, x in enumerate(entered3):
            for y in entered3[i + 1:]:
                vx, vy = mapped(x, wide[x]), mapped(y, wide[y])
                ok = ~vx.isin(NONCONCRETE) & ~vy.isin(NONCONCRETE)
                v = cramers_v(vx[ok], vy[ok]) if ok.sum() >= 10 else float("nan")
                pairs.append((x, y, v, int(ok.sum())))
        for n in m:
            mine = [(p[1] if p[0] == n else p[0], p[2]) for p in pairs if n in p[:2]
                    and not math.isnan(p[2])]
            if n in entered3 and mine:
                other, v = max(mine, key=lambda t: t[1])
                m[n]["max_cramers_v"], m[n]["max_cramers_v_with"] = v, other
            else:
                m[n]["max_cramers_v"], m[n]["max_cramers_v_with"] = float("nan"), None

        for x, y, v, nboth in sorted(pairs, key=lambda p: -(p[2] if not math.isnan(p[2]) else -1)):
            if math.isnan(v) or v <= ccfg["max_cramers_v"]:
                continue
            if m[x]["status"] != "kept" or m[y]["status"] != "kept":
                continue
            kx = (m[x]["coverage"], m[x]["reliability"], x)
            ky = (m[y]["coverage"], m[y]["reliability"], y)
            loser, winner = (y, x) if kx > ky else (x, y)
            drop(loser, 3, f"Cramer's V {v:.3f} > {ccfg['max_cramers_v']} with '{winner}' "
                           f"(n={nboth}); kept the one with higher coverage")

    def f_reliability():
        # 4 reliability
        for n in alive():
            if m[n]["reliability"] < ccfg["min_reliability"]:
                drop(n, 4, f"reliability {m[n]['reliability']:.3f} < {ccfg['min_reliability']}")

    def f_none_artifact():
        # 5 physician-category "none" artifact
        for n in m:
            col = mapped(n, wide[n])
            art = []
            for v in [v for v in mapping[n] if mapping[n][v] == v]:
                ids = col[col == v].index
                share = float(np.mean([phys[p] == "none" for p in ids])) if len(ids) else 0.0
                if share > ccfg["none_overlap_max"]:
                    art.append((v, share, len(ids)))
            m[n]["none_artifact_values"] = art
            if m[n]["status"] != "kept":
                continue
            for v, _, _ in art:
                mapping[n][v] = OTHER
            meaningful = [v for v in mapping[n] if mapping[n][v] == v]
            if art and len(meaningful) < 2:
                drop(n, 5, f"values {[a_[0] for a_ in art]} are > {ccfg['none_overlap_max']} "
                           f"'none'; {len(meaningful)} meaningful value(s) left")

    order = ccfg.get("filter_order") or ["coverage", "support", "redundancy",
                                          "reliability", "none_artifact"]
    if order[:2] != ["coverage", "support"] or sorted(order[2:]) != \
            ["none_artifact", "redundancy", "reliability"]:
        die(f"unsupported curation.filter_order {order}")
    for fname in order[2:]:
        {"redundancy": f_redundancy, "reliability": f_reliability,
         "none_artifact": f_none_artifact}[fname]()

    # sliceability (display only)
    for n in m:
        col = mapped(n, wide[n])
        counts = Counter(col[~col.isin(NONCONCRETE)])
        m[n]["entropy"] = norm_entropy(counts)
        m[n]["final_value_counts_sample"] = dict(counts)
        rel_ = m[n]["reliability"] if not math.isnan(m[n]["reliability"]) else 0.0
        m[n]["sliceability"] = (m[n]["coverage"] + m[n]["entropy"] + rel_) / 3
        m[n]["value_map"] = mapping[n]

    cols = ["attribute", "question", "gate", "values", "coverage", "min_support",
            "max_cramers_v", "reliability", "cross_model_agreement", "entropy", "sliceability",
            "status", "drop_reason"]
    extra = ["column", "dropped_at_filter", "max_cramers_v_with", "n_gate_yes", "n_unknown",
             "n_na", "n_parse_error", "reliability_n", "n_meaningful_after_support",
             "folded_into_other_support", "none_artifact_values", "final_value_counts_sample"]
    tab = pd.DataFrame([m[n] for n in m])
    for c in extra:
        if c not in tab.columns:
            tab[c] = None
    tab[cols + extra].to_csv(run.path("attribute_metrics.csv"), index=False)
    write_meta(run, run.path("attribute_metrics.csv"), "5", thresholds=ccfg)

    final = []
    for n in alive():
        a = by_attr[n]
        meaningful = [v for v in mapping[n] if mapping[n][v] == v]
        final.append({"name": n, "column": slug(n), "question": a["question"],
                      "gate": a["gate"],
                      "prompt_values": [v["value"] for v in a["values"]],
                      "values": meaningful + [OTHER],
                      "value_map": mapping[n], "merged_from": a.get("merged_from"),
                      "hypothesis": a.get("hypothesis"),
                      "metrics": {k: m[n][k] for k in ("coverage", "min_support", "max_cramers_v",
                                                       "reliability", "cross_model_agreement",
                                                       "entropy", "sliceability")},
                      "folded_sample": m[n]["folded_into_other_support"],
                      "value_counts_sample": m[n]["final_value_counts_sample"]})
    cols_seen = Counter(f["column"] for f in final)
    if any(v > 1 for v in cols_seen.values()):
        die(f"column name collision among final attributes: {cols_seen}")
    write_json(run.path("attributes_final.json"),
               {"attributes": final, "sample_ids_n": len(sample), "reliability_ids_n": len(rel),
                "annotation_model": llm.model, "reliability_model": llm_rel.model,
                "second_model": acfg.get("second_model"),
                "seed": acfg["seed"], "reliability_seed": acfg["reliability_seed"]})
    write_meta(run, run.path("attributes_final.json"), "5", n_final=len(final))
    st = Counter((m[n]["status"], m[n]["dropped_at_filter"]) for n in m)
    log(f"5: {len(merged)} attributes in, {len(final)} kept; by filter {dict(st)}")
