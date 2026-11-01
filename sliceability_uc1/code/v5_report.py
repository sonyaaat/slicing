"""REPORT_corpus_run1.md for the v5 corpus run. No HealthBench prompt text: no notes, no
evidence quotes, no evidence spans, no user text. Attribute names and value labels are
model-written and are shown. Sections 3 (new vs reworded) and 12 (judgement) carry
numeric aids and a placeholder for the written judgement, added after reading the run."""

from __future__ import annotations

import json
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

from common import NA, PARSE_ERROR, UNKNOWN, Run, log, read_json, read_jsonl
from v5_annotate import NOT_STATED

PLACEHOLDER = "_[Judgement pending: to be written by Claude after reading this run's outputs.]_"


def md(df: pd.DataFrame, floatfmt: int = 3) -> str:
    if df is None or not len(df):
        return "_(empty)_\n"
    d = df.copy()
    for c in d.columns:
        if d[c].dtype.kind == "f":
            d[c] = d[c].map(lambda x: "" if pd.isna(x) else f"{x:.{floatfmt}f}")
    cols = [str(c) for c in d.columns]
    out = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    for r in d.itertuples(index=False):
        out += "| " + " | ".join(str(x).replace("|", "/").replace("\n", " ") for x in r) + " |\n"
    return out


def _exists(run, f):
    return run.path(f).exists()


def run(run: Run) -> None:
    L = []
    cfg = run.cfg
    L.append("# Sliceability v5 — corpus run 1\n")
    L.append(f"Run directory `{run.dir.name}`. Prompt version `{cfg['prompts']['version']}`. "
             f"Canary `{cfg['canary']}`. Spec: *Sliceability v5: універсальні атрибути на всьому "
             "корпусі*. Step 7 (confirmation) was not run; the confirmation split was not read "
             "except by step 0 (R² on the whole corpus, by spec), the split's balance check, and "
             "the synthetic level A, which per spec uses all 4,027 rows and runs after the "
             "preregistration.\n")

    # 1 ---------------------------------------------------------------
    L.append("## 1. Step 0 — explained variance and target\n")
    if _exists(run, "step0_r2.csv"):
        t = pd.read_csv(run.path("step0_r2.csv"))
        piv = t.pivot_table(index="target", columns="partition", values="r2_cv_mean")
        piv = piv[["corpus"] + [c for c in piv.columns if c != "corpus"]]
        piv.columns = [c.replace("theme:", "") for c in piv.columns]
        L.append("5-fold CV R² (mean over held-out folds), ridge on bge-m3 embeddings of the user "
                 "turns; alpha chosen inside each training fold. Raw overall scores are shown for "
                 "the corpus only (within a theme they equal the relative scores).\n")
        L.append(md(piv.reset_index()))
        c = t[t.partition == "corpus"][["target", "n", "r2_cv_mean", "r2_cv_sd", "r2_oof", "alpha_median"]]
        L.append("\nCorpus detail:\n")
        L.append(md(c))
        r = cfg.get("step0_result", {})
        L.append(f"\n**Chosen target: `{cfg.get('target')}`.** Reason: {r.get('reason')}\n")

    # 2 ---------------------------------------------------------------
    L.append("## 2. Data and split\n")
    if _exists(run, "step2_split_summary.json"):
        s = read_json(run.path("step2_split_summary.json"))
        ch = read_json(run.path("step1_checks.json"))
        L.append(f"Integrity checks (step 1): user text identical {ch['user_text_identical']}, rubric "
                 f"identical {ch['rubric_identical']}, recomputed score max diff "
                 f"{ch['recomputed_score_maxabsdiff_gpt']:.1e} / {ch['recomputed_score_maxabsdiff_claude']:.1e}.\n")
        bt = pd.DataFrame(s["by_theme"]).T.reset_index().rename(columns={"index": "theme"})
        bt["theme mean score_mean"] = bt.theme.map(ch["theme_mean_score_mean"])
        bt["share physician 'none'"] = bt.theme.map(ch["physician_category_none_by_theme"])
        L.append(md(bt))
        L.append(f"\nTotal: {s['counts']}. Stratified by theme × within-theme quartile of `{s['target']}`, "
                 f"seed {s['seed']}. Balance check KS on the target: D = {s['ks_target']['D']:.4f}, "
                 f"p = {s['ks_target']['p']:.3f}.\n")

    # 3 ---------------------------------------------------------------
    L.append("## 3. Discovery\n")
    if _exists(run, "step3_contrast.json"):
        ci = read_json(run.path("step3_contrast.json"))
        L.append(f"Contrast on `{ci['target']}` (discovery): LOW ≤ {ci['q_low']:.4f} (n = {ci['n_low']}), "
                 f"HIGH ≥ {ci['q_high']:.4f} (n = {ci['n_high']}), middle {ci['n_middle']}.\n")
        L.append(md(pd.DataFrame({"LOW": ci["low_by_theme"], "HIGH": ci["high_by_theme"]}).reset_index()
                    .rename(columns={"index": "theme"})))
    if _exists(run, "notes.jsonl"):
        nr = read_jsonl(run.path("notes.jsonl"))
        L.append(f"\n3a: {sum(1 for r in nr if r.get('facts'))} notes, "
                 f"{sum(1 for r in nr if not r.get('facts'))} failed.\n")
    if _exists(run, "candidates_raw.json"):
        cr = read_json(run.path("candidates_raw.json"))
        nov = {}
        try:
            from step4_merge import _embed
            cands = cr["candidates"]
            emb, _ = _embed([f"{c['name']}. {c['question']}" for c in cands], cfg["merge"]["embedding_model"])
            for i, c in enumerate(cands):
                prev = [j for j, o in enumerate(cands) if o["round"] < c["round"]]
                if prev:
                    j = max(prev, key=lambda j: float(emb[i] @ emb[j]))
                    nov[c["cid"]] = (float(emb[i] @ emb[j]), cands[j]["name"])
        except Exception as e:                       # report must not fail on the aid
            L.append(f"_(novelty aid not computed: {e})_\n")
        rows = []
        for c in cr["candidates"]:
            n = nov.get(c["cid"])
            rows.append({"round": c["round"], "attribute": c["name"],
                         "values": " / ".join(v["value"] for v in c["values"]),
                         "max cos to earlier round": n[0] if n else np.nan,
                         "nearest earlier": n[1] if n else ""})
        L.append("\nRound sizes: " + ", ".join(f"round {e['round']}: {e['n_attributes']} "
                                               f"(LOW {e['n_low']}, HIGH {e['n_high']})" for e in cr["rounds"]) + "\n")
        L.append("\nAll proposed attributes (cosine of name+question to the nearest attribute of an "
                 "earlier round is an aid, not a rule):\n")
        L.append(md(pd.DataFrame(rows)))
        L.append("\n**New vs reworded (judgement).** " + PLACEHOLDER + "\n")

    # 4 ---------------------------------------------------------------
    L.append("## 4. Critique\n")
    if _exists(run, "critique.json"):
        cj = read_json(run.path("critique.json"))
        t = pd.DataFrame(cj["scores"])[["round", "name", "concreteness", "distinctness", "plainness",
                                        "breadth", "factor", "status", "duplicate_of", "drop_reason"]]
        L.append(f"Notes sample {cj['sample_n']} (by theme {cj['sample_by_theme']}; groups "
                 f"{cj['sample_groups']}). Filter scores {cj['filter_scores']} ≥ {cj['min_score']}; "
                 "distinctness decides kept / duplicate as in run 4; factor reported only.\n")
        L.append(md(t))
        L.append("\nMissing attributes proposed by the critic:\n")
        L.append(md(pd.DataFrame([{"name": m["name"], "question": m["question"],
                                   "values": " / ".join(v["value"] for v in m["values"])}
                                  for m in cj["missing_with_evidence"]])))

    # 5 ---------------------------------------------------------------
    L.append("## 5. Verification\n")
    if _exists(run, "candidates_verified.json"):
        vj = read_json(run.path("candidates_verified.json"))
        rows = []
        for status, lst in (("universal", vj["attributes"]), ("thematic_pool", vj["thematic_pool"]),
                            ("dropped", vj["dropped"])):
            for c in lst:
                for v in c["values"]:
                    rows.append({"attribute": c["name"], "status": status, "value": v["value"],
                                 "confirmed/total": f"{v['n_confirmed']}/{v['n_evidence']}",
                                 "value status": v["status"],
                                 "themes (attr)": c.get("n_evidence_themes")})
        L.append(md(pd.DataFrame(rows)))
        L.append("\nTheme spread of confirmed evidence per attribute:\n")
        L.append(md(pd.DataFrame([{"attribute": c["name"], "status": c["status_3d"],
                                   "themes": ", ".join(c["evidence_themes"]),
                                   "reason": c.get("drop_reason_3d") or ""}
                                  for c in vj["attributes"] + vj["thematic_pool"] + vj["dropped"]])))

    # 6 ---------------------------------------------------------------
    L.append("## 6. Merge\n")
    if _exists(run, "candidates_merged.json"):
        mj = read_json(run.path("candidates_merged.json"))
        L.append(f"{mj['n_input']} universal attributes → {mj['n_clusters']} clusters; clusters: "
                 + "; ".join("+".join(x) for x in mj["clusters"] if len(x) > 1) + "\n")
        ch = [r for r in mj["label_map"] if r.get("new_label") != r.get("old_label")]
        L.append("\nLabels that changed (old → new):\n")
        L.append(md(pd.DataFrame(ch)))
        L.append(f"\nVerbatim reverts (reply rewrote a label without comma/or): "
                 f"{sum('reverted' in r['how'] for r in mj['label_map'])}.\n")
        L.append("\nMerged attributes:\n")
        L.append(md(pd.DataFrame([{"attribute": a["name"], "status": a["status"],
                                   "values": " / ".join(a["prompt_values"]),
                                   "merged_from": ", ".join(a["merged_from"])}
                                  for a in mj["attributes"] + mj["dropped"]])))

    # 7 ---------------------------------------------------------------
    L.append("## 7. Curation\n")
    if _exists(run, "attribute_metrics.csv"):
        t = pd.read_csv(run.path("attribute_metrics.csv"))
        cov_cols = [c for c in t.columns if c.startswith("coverage_")]
        keep = ["attribute", "coverage"] + cov_cols + ["min_support", "reliability", "cross_model_agreement",
                                                       "max_cramers_v", "max_cramers_v_with", "sliceability",
                                                       "status", "drop_reason"]
        tt = t[keep].copy()
        tt.columns = [c.replace("coverage_", "cov ") for c in tt.columns]
        L.append(md(tt))
    if _exists(run, "annotations_full_long.csv"):
        lg = pd.read_csv(run.path("annotations_full_long.csv"))
        fin = read_json(run.path("attributes_final.json"))["attributes"]
        L.append("\n### Final attributes — value distribution on all 4,027 and per theme (share)\n")
        for a in fin:
            s = lg[lg.attribute == a["name"]]
            tab = pd.crosstab(s.value_final, s.theme, normalize="columns")
            tab.insert(0, "corpus", s.value_final.value_counts(normalize=True))
            tab.insert(0, "n", s.value_final.value_counts())
            L.append(f"\n**{a['name']}** — {a['question']}" +
                     (" (excluded from tables)" if a.get("excluded_from_et") else "") + "\n")
            L.append(md(tab.reset_index().rename(columns={"value_final": "value"})))

        # 8 -----------------------------------------------------------
        L.append("## 8. not_applicable and not_stated shares (full annotation)\n")
        rows = []
        for a in fin:
            s = lg[lg.attribute == a["name"]]
            for th, g in [("corpus", s)] + list(s.groupby("theme")):
                rows.append({"attribute": a["name"], "theme": th,
                             "not_applicable": (g.value == NA).mean(),
                             "not_stated": (g.value == NOT_STATED).mean(),
                             "unknown": (g.value == UNKNOWN).mean(),
                             "parse_error": (g.value == PARSE_ERROR).mean()})
        r8 = pd.DataFrame(rows)
        for k in ("not_applicable", "not_stated"):
            L.append(f"\n{k}:\n")
            p = r8.pivot(index="attribute", columns="theme", values=k)
            L.append(md(p[["corpus"] + [c for c in p.columns if c != "corpus"]].reset_index()))
        L.append("\nunknown + parse_error (corpus): " + ", ".join(
            f"{r.attribute} {r.unknown + r.parse_error:.3f}" for r in r8[r8.theme == "corpus"].itertuples()) + "\n")

    # 9 ---------------------------------------------------------------
    L.append("## 9. Explanation tables (discovery split)\n")
    pre = read_json(run.path("preregistered_rules.json")) if _exists(run, "preregistered_rules.json") else None
    if pre:
        L.append(f"Preregistered {len(pre['rules'])} rules at {pre['registered_at_utc']} (UTC). Rule: {pre['rule']}\n")
        L.append(md(pd.DataFrame([{"id": r["id"], "kind": r["kind"], "rule": r["rule"],
                                   "tables": ",".join(r["tables"]), "support": r["support_discovery"],
                                   "dev gpt": r.get("deviation_gpt", np.nan),
                                   "dev claude": r.get("deviation_claude", np.nan),
                                   "dev diff": r.get("deviation_diff", np.nan)} for r in pre["rules"]])))
    reg = {r["rule_columns"]: r["id"] for r in (pre or {}).get("rules", [])}
    for spec in cfg["et"]["tables"]:
        f = run.path(f"et_{spec['name']}.csv")
        if not f.exists():
            continue
        from v5_tables import read_et
        t = read_et(f)
        meta = read_json(run.path(f"et_{spec['name']}_partition_mean.json"))
        L.append(f"\n### et_{spec['name']} — target `{meta['target']}`, discovery n = {meta['n']}, "
                 f"mean {meta['mean_target']:+.4f}, |effect| ≥ {meta['min_effect']}, ≤ {meta['max_conj']} "
                 f"conditions; {meta['n_eligible_patterns']} eligible patterns\n")
        if len(t):
            t["prereg"] = t.rule_columns.map(lambda x: f"#{reg[x]}" if x in reg and not spec["name"].endswith("conj3") else "")
            sh = t[["step", "prereg", "rule", "support", "deviation", "deviation_gpt", "deviation_claude",
                    "n_themes", "perm_p", "perm_p_bh"]]
            L.append(md(sh))
            ax = [c for c in t.columns if c.startswith("axisdev_")]
            worst = t[ax].apply(lambda r: r.abs().idxmax() if r.notna().any() else "", axis=1)
            L.append("\nAxis with the largest |deviation| per row: " + "; ".join(
                f"{s}: {w.replace('axisdev_', '')}" for s, w in zip(t.step, worst)) + "\n")
        else:
            L.append("_(no row passed support and effect thresholds)_\n")

    # 10 --------------------------------------------------------------
    L.append("## 10. Synthetic level A\n")
    if _exists(run, "synthetic_a.csv"):
        sa = pd.read_csv(run.path("synthetic_a.csv"))
        sj = read_json(run.path("synthetic_a_summary.json"))
        L.append(f"Target `{sj['target']}` on all {sj['n']} messages; unplanted table has {sj['baseline_rows']} rows "
                 "(not shown). recall@3 exact: the planted single condition is among the first 3 rows; "
                 "contains: a first-3 row contains it. precision = planted rows / (planted + spurious).\n")
        L.append(md(pd.DataFrame(sj["by_delta"])))
        L.append("\nPer test:\n")
        L.append(md(sa))

    # 11 --------------------------------------------------------------
    L.append("## 11. Cost, time, cache\n")
    if _exists(run, "calls.jsonl"):
        c = pd.DataFrame(read_jsonl(run.path("calls.jsonl")))
        c = c[c.get("event").isna()] if "event" in c.columns else c
        g = c.groupby(["step", "model"]).agg(calls=("ts", "size"), cache_hits=("cached", "sum"),
                                             tokens_in=("tokens_in", "sum"), tokens_out=("tokens_out", "sum"),
                                             cost_usd=("cost_usd", "sum"), failed=("ok", lambda x: int((~x.astype(bool)).sum())))
        L.append(md(g.reset_index(), 4))
        L.append(f"\nTotal cost ${c.cost_usd.sum():.2f}; API calls {int((~c.cached.astype(bool)).sum())}, "
                 f"cache hits {int(c.cached.astype(bool).sum())}.\n")
    if _exists(run, "checkpoint.json"):
        ck = read_json(run.path("checkpoint.json"))
        L.append("\nWall-clock per step (s): " + ", ".join(f"{k} {v}" for k, v in ck["step_seconds"].items()) + "\n")
    if _exists(run, "decisions.log"):
        L.append("\nDecisions taken by the run (`decisions.log`):\n\n```\n" + run.path("decisions.log").read_text() + "```\n")

    # 12 --------------------------------------------------------------
    L.append("## 12. Judgement\n")
    L.append(PLACEHOLDER + "\n")
    run.path("REPORT_corpus_run1.md").write_text("\n".join(L))
    log("report written: REPORT_corpus_run1.md")
