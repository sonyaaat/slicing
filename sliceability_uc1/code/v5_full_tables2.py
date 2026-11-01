"""Full-data explanation tables on subset S2, version 2. No model call. No split.

Changes from v5_full_tables.py (v1, kept in subset_s2/full_tables/):
  * not_stated is excluded from rules, like other / not_applicable / unknown / parse_error /
    "none of these". On the run-4 attributes the five absence labels that mean the same
    ("no age wording", "no place named", "No action stated", "no onset-speed wording",
    "no explicit request") are excluded too.
  * up to 10 rows; corpus support >= 40, theme support >= 20; |effect| >= 0.05 corpus,
    >= 0.08 theme (as before).
  * extra columns: worst axis (definition of v5_step7), context_awareness in the slice vs
    the scope mean for both models (theme-centred axis_rel_* on corpus tables, absolute
    axis_* on theme tables; messages with a context_awareness criterion only), and the
    number of themes with >= 10 items in the slice.
  * emergency_referrals: the 14 run-4 attributes (runs/20261016T235755Z/annotations_full.csv,
    joined by prompt_id) are added as theme-level attributes; replicated is checked against
    run 4 step 7 too.
  * every previously confirmed rule that applies to the scope and is not a table row is
    appended, flagged crowded_out, with its stats and the reason it is not in the table.

Version v5: emergency_referrals only, as in v2, but the theme attributes come from the v5 theme
run (THEME_V5, runs/20261028T201353Z: the corpus-run pipeline inside the theme) instead of run 4.
Run 4's step-7 rules are not a replication source; the theme run has no step 7.

Version v6: as v5, but the search uses only the theme-run attributes (no universal attribute).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RUNS_DIR, Run, die, log, write_json, write_meta  # noqa: E402
from et import bh, permutation_p  # noqa: E402
from v5_full_tables import conds_of, key_of  # noqa: E402
from v5_infra import decide, utcnow  # noqa: E402
from v5_step7 import axis_shares, worst_axis  # noqa: E402
from v5_subset import ATTRS, FORM_EXCLUDED, NONAPPL, TRIPLE, md  # noqa: E402
from v5_tables import mask_of, search  # noqa: E402

MODELS = ("gpt", "claude", "mean")
RUN4 = "20261016T235755Z"
THEME_V5 = "20261028T201353Z"         # v5 theme run on emergency_referrals (table version v5)
R4_ABSENCE = ["no age wording", "no place named", "No action stated", "no onset-speed wording",
              "no explicit request"]
EXCLUDE = ["unknown", "not_applicable", "parse_error", "other", "none of these", "not_stated"]
MAX_CONJ, MAX_ROWS, PERM_N, PERM_SEED = 2, 10, 10000, 42


def load(run: Run, theme_run: str = RUN4):
    df = pd.read_csv(run.path("corpus_data.csv"))
    ann = pd.read_csv(run.path("annotations_full.csv"), keep_default_na=False)
    full = df.merge(ann.drop(columns="theme"), on="prompt_id").sort_values("prompt_id").reset_index(drop=True)
    a4 = pd.read_csv(RUNS_DIR / theme_run / "annotations_full.csv", keep_default_na=False)
    a4 = a4.drop(columns=[c for c in ("split", "theme") if c in a4.columns])
    r4_cols = [c for c in a4.columns if c != "prompt_id"]
    if set(r4_cols) & set(full.columns):
        die("theme-run attribute names collide with corpus columns")
    full = full.merge(a4, on="prompt_id", how="left")
    in_s2 = (sum((~full[c].isin(NONAPPL)).astype(int) for c in TRIPLE) >= 2).to_numpy()
    if int(in_s2.sum()) != run.cfg["subset_s2"]["n"]:
        die("S2 size differs from run_config subset_s2.n")
    er = full[in_s2 & (full.theme == "emergency_referrals").to_numpy()]
    if er[r4_cols].isna().any().any():
        die("some emergency_referrals S2 items have no theme-run annotation")
    return full, in_s2, r4_cols


def sources(run: Run, run4: bool = True) -> dict[str, list[tuple[frozenset, str, str]]]:
    """label -> [(key, rule text, rule_columns)] of rules confirmed on a held-out split."""
    files = {"main step 7": [(run.path("FINAL_TABLE_CORPUS.csv"), None)],
             "S2 step 7 corpus": [(run.path("subset_s2/FINAL_TABLE_corpus.csv"), None)],
             "S2 step 7 emergency_referrals": [(run.path("subset_s2/FINAL_TABLE_theme_emergency_referrals.csv"), "emergency_referrals")],
             "S2 step 7 communication": [(run.path("subset_s2/FINAL_TABLE_theme_communication.csv"), "communication")],
             "run 4 step 7": [(RUNS_DIR / RUN4 / "FINAL_TABLE_UC1.csv", "emergency_referrals")]}
    if not run4:
        del files["run 4 step 7"]
    out = {}
    for label, lst in files.items():
        out[label] = []
        for f, theme in lst:
            ft = pd.read_csv(f)
            for r in ft.itertuples():
                out[label].append((key_of(conds_of(r.rule_columns), theme), r.rule, r.rule_columns))
    return out


def scope_conds(key: frozenset, theme: str | None):
    """Conditions of a confirmed rule in the scope's terms, or None if it does not apply."""
    if theme is None:
        return sorted(key)
    if ("theme", theme) not in key:
        return None
    return sorted(c for c in key if c[0] != "theme")


def row_stats(sub, mk, y, tgt, fam, ca_col, clip_mean_m, shares, cols_in_scope):
    dev = float(y[mk].mean() - y.mean()) if mk.any() else np.nan
    r = {"n": int(mk.sum()),
         "mean_gpt": float(sub[f"{fam}_gpt"][mk].mean()), "mean_claude": float(sub[f"{fam}_claude"][mk].mean()),
         "abs_mean_gpt": float(sub.score_gpt[mk].mean()), "abs_mean_claude": float(sub.score_claude[mk].mean()),
         "dev_pts": 100 * dev, "dev_pct": 100 * dev / clip_mean_m}
    for m in ("gpt", "claude"):
        s = sub[ca_col.format(m=m)]
        r[f"ca_{m}_slice"] = float(s[mk].mean()) if s[mk].notna().any() else np.nan
        r[f"ca_{m}_scope"] = float(s.mean())
    r["ca_n_slice"] = int(sub[ca_col.format(m="gpt")][mk].notna().sum())
    if mk.any():
        a, term, n_a, _ = worst_axis(shares, sub, mk)
        r.update(worst_axis=a, worst_axis_pts=100 * term, worst_axis_n=n_a)
    else:
        r.update(worst_axis="", worst_axis_pts=np.nan, worst_axis_n=0)
    vc = sub.loc[mk, "theme"].value_counts()
    r["themes_ge10"] = int((vc >= 10).sum())
    return r


def run(run_dir: Path, version: str = "v2") -> None:
    """v2: all three scopes, theme allowed on corpus. v3: corpus scope only, theme NOT a rule
    attribute (themes_ge10 column kept); theme tables stay as in v2. v5: emergency_referrals
    only, theme attributes from the v5 theme run. v6: as v5, theme-run attributes only."""
    if version not in ("v2", "v3", "v4", "v5", "v6"):
        die(f"unknown version {version}")
    run = Run(run_dir)
    out = run.path(f"subset_s2/full_tables_{version}")
    if out.exists() and any(out.iterdir()):
        die(f"{out} is not empty")
    out.mkdir(parents=True, exist_ok=True)
    t0 = utcnow()
    v5like = version in ("v5", "v6")
    theme_run = THEME_V5 if v5like else RUN4
    full, in_s2, r4_cols = load(run, theme_run)
    if v5like:
        fin_t = json.loads((RUNS_DIR / theme_run / "attributes_final.json").read_text())["attributes"]
        r4_cols = [a["column"] for a in fin_t if not a.get("excluded_from_et")]
    shares_full = axis_shares(run, full)          # theme-centred over all 4,027, as in step 7
    s2 = full[in_s2].reset_index(drop=True)
    sh_s2 = {m: v[in_s2].reset_index(drop=True) for m, v in shares_full.items()}
    fin = json.loads(run.path("attributes_final.json").read_text())["attributes"]
    fin4 = json.loads((RUNS_DIR / theme_run / "attributes_final.json").read_text())["attributes"]
    col2name = {a["column"]: a["name"] for a in fin} | {a["column"]: a["name"] for a in fin4} | {"theme": "theme"}
    src = sources(run, run4=not v5like)
    # the run-4 absence labels belong to run 4; the v5 theme run maps absence wording to not_stated in step 4
    absence = [] if v5like else R4_ABSENCE
    exclude_all = EXCLUDE + absence
    scopes = [
        {"key": "corpus", "theme": None, "family": "score_rel", "cols": ATTRS + ["theme"], "min_support": 40,
         "min_effect": 0.05, "ca": "axis_rel_context_awareness_{m}",
         "src": ["main step 7", "S2 step 7 corpus"]},
        {"key": "theme_emergency_referrals", "theme": "emergency_referrals", "family": "score",
         "cols": ATTRS + r4_cols, "min_support": 20, "min_effect": 0.08, "ca": "axis_context_awareness_{m}",
         "src": ["main step 7", "S2 step 7 corpus", "S2 step 7 emergency_referrals", "run 4 step 7"]},
        {"key": "theme_communication", "theme": "communication", "family": "score", "cols": ATTRS,
         "min_support": 20, "min_effect": 0.08, "ca": "axis_context_awareness_{m}",
         "src": ["main step 7", "S2 step 7 corpus", "S2 step 7 communication"]},
    ]
    if version in ("v3", "v4"):
        scopes = [scopes[0] | {"cols": list(ATTRS)}]
    if v5like:
        scopes = [scopes[1] | {"src": ["main step 7", "S2 step 7 corpus", "S2 step 7 emergency_referrals"]}]
    if version == "v6":
        scopes = [scopes[0] | {"cols": list(r4_cols)}]
    max_conj = 3 if version == "v4" else MAX_CONJ
    all_keys: dict[frozenset, list[str]] = {}
    for label, lst in src.items():
        for k, _, _ in lst:
            all_keys.setdefault(k, []).append(label)

    summary = {"version": version, "theme_run": theme_run, "max_conj": max_conj, "started_at_utc": t0, "n_s2": int(len(s2)), "split_used": "none (all items of the scope)",
               "exclude_values": EXCLUDE, "run4_absence_labels_excluded": absence,
               "replication_sources": {k: len(v) for k, v in src.items()},
               "params": {"max_conj": MAX_CONJ, "max_rows": MAX_ROWS, "permutation_n": PERM_N,
                          "permutation_seed": PERM_SEED,
                          "scopes": [{k: v for k, v in s.items()} for s in scopes]}, "tables": {}}
    rep = []
    for sc in scopes:
        tmask = np.ones(len(s2), bool) if sc["theme"] is None else (s2.theme == sc["theme"]).to_numpy()
        data = s2[tmask].reset_index(drop=True)
        sh = {m: v[tmask].reset_index(drop=True) for m, v in sh_s2.items()}
        clip_mean = {m: float(data[f"score_{m}"].mean()) for m in MODELS}
        for m in MODELS:
            tgt = f"{sc['family']}_{m}"
            res, ok, lo, hi = search(data, sc["cols"], tgt, max_conj=max_conj, min_support=sc["min_support"],
                                     min_effect=sc["min_effect"], max_rows=MAX_ROWS, exclude=exclude_all)
            if not ok.all():
                die(f"{tgt}: missing target values")
            y = data[tgt].to_numpy(float)
            star = {c: "*" for c in sc["cols"]}
            rows = [{"row_type": "baseline", "step": 0, **star,
                     **row_stats(data, np.ones(len(data), bool), y, tgt, sc["family"], sc["ca"], clip_mean[m], sh, sc["cols"]),
                     "p_perm": np.nan, "p_bh": np.nan, "replicated": "", "replicated_in": "", "reason": "",
                     "rule_columns": "(all items)"}]
            rows[0].update(worst_axis="", worst_axis_pts=np.nan, worst_axis_n=0)
            pv, in_table = [], set()
            for r in res["rows"]:
                mk = mask_of(data, r["pattern"])
                p = permutation_p(y, mk, PERM_N, PERM_SEED + r["step"])
                pv.append(p)
                k = key_of(r["pattern"], sc["theme"])
                in_table.add(k)
                hits = sorted(set(all_keys.get(k, [])))
                rows.append({"row_type": "greedy", "step": r["step"], **star, **{a: v for a, v in r["pattern"]},
                             **row_stats(data, mk, y, tgt, sc["family"], sc["ca"], clip_mean[m], sh, sc["cols"]),
                             "p_perm": p, "p_bh": np.nan, "replicated": bool(hits), "replicated_in": "; ".join(hits),
                             "reason": "", "rule_columns": " AND ".join(f"{a}={v}" for a, v in r["pattern"])})
            for row, a in zip(rows[1:], bh(pv)):
                row["p_bh"] = a
            # previously confirmed rules not in the table
            seen = set()
            for label in sc["src"]:
                for k, rule, rc in src[label]:
                    conds = scope_conds(k, sc["theme"])
                    if conds is None or k in in_table or k in seen:
                        continue
                    seen.add(k)
                    if any(a not in data.columns for a, _ in conds):
                        continue
                    mk = mask_of(data, conds)
                    reasons = []
                    if len(conds) > max_conj:
                        reasons.append(f"{len(conds)} conditions")
                    if any(a not in sc["cols"] for a, _ in conds):
                        reasons.append("attribute not in search (" + ", ".join(a for a, _ in conds if a not in sc["cols"]) + ")")
                    if any(v in exclude_all for _, v in conds):
                        reasons.append("excluded value (" + ", ".join(v for _, v in conds if v in exclude_all) + ")")
                    if mk.sum() < sc["min_support"]:
                        reasons.append(f"support {int(mk.sum())} < {sc['min_support']}")
                    dev = float(y[mk].mean() - y.mean()) if mk.any() else 0.0
                    if abs(dev) < sc["min_effect"]:
                        reasons.append(f"|effect| {abs(dev):.3f} < {sc['min_effect']}")
                    reason = "; ".join(reasons) or "eligible, not selected by greedy"
                    p = permutation_p(y, mk, PERM_N, PERM_SEED + 100 + len(rows)) if 0 < mk.sum() < len(y) else np.nan
                    rows.append({"row_type": "crowded_out", "step": np.nan, **star, **{a: v for a, v in conds},
                                 **row_stats(data, mk, y, tgt, sc["family"], sc["ca"], clip_mean[m], sh, sc["cols"]),
                                 "p_perm": p, "p_bh": np.nan, "replicated": True,
                                 "replicated_in": "; ".join(sorted(set(all_keys[k]))), "reason": reason,
                                 "rule_columns": " AND ".join(f"{a}={v}" for a, v in conds)})
            for row in rows:
                if row["row_type"] == "baseline":
                    continue
                conds = conds_of(row["rule_columns"])
                if len(conds) != 3:
                    continue
                mk3 = mask_of(data, conds)
                dev3 = float(y[mk3].mean() - y.mean())
                best = None
                for drop in range(3):
                    sub_c = [c for i, c in enumerate(conds) if i != drop]
                    mk2 = mask_of(data, sub_c)
                    dev2 = float(y[mk2].mean() - y.mean())
                    if best is None or np.sign(dev3) * dev2 > np.sign(dev3) * best[2]:
                        best = (sub_c, conds[drop], dev2, mk2)
                sub_c, third, dev2, mk2 = best
                y2 = y[mk2]
                inside = mk3[mk2]
                p_in = permutation_p(y2, inside, PERM_N, PERM_SEED + 500 + int(mk3.sum())) \
                    if 0 < inside.sum() < len(y2) else np.nan
                row.update(sub_rule=" AND ".join(f"{a}={v}" for a, v in sub_c), sub_n=int(mk2.sum()),
                           sub_dev_pts=100 * dev2, third_condition=f"{third[0]}={third[1]}",
                           delta_pts=100 * (dev3 - dev2), kept_share=float(mk3.sum() / mk2.sum()),
                           rest_of_sub_dev_pts=100 * float(y2[~inside].mean() - y.mean()) if (~inside).any() else np.nan,
                           sub_meets_support=bool(mk2.sum() >= sc["min_support"]),
                           sub_meets_effect=bool(abs(dev2) >= sc["min_effect"]), p_third_within_sub=p_in)
            tab = pd.DataFrame(rows)
            name = f"et_full_{sc['key']}_{m}"
            tab.to_csv(out / f"{name}.csv", index=False)
            g = tab[tab.row_type == "greedy"]
            meta = {"scope": sc["key"], "target": tgt, "n": int(len(data)), "scope_mean_target": float(y.mean()),
                    "scope_mean_clipped": clip_mean[m], "rescale_range": [lo, hi],
                    "n_candidate_patterns": res["n_candidates"], "n_eligible_patterns": res["n_eligible"],
                    "min_support": sc["min_support"], "min_effect": sc["min_effect"], "rows": int(len(g)),
                    "n_replicated": int((g.replicated == True).sum()),  # noqa: E712
                    "n_crowded_out": int((tab.row_type == "crowded_out").sum())}
            write_meta(run, out / f"{name}.csv", f"subset-full-{version}", api_calls=0, **meta,
                       split="none: all S2 items of the scope",
                       note="p ignores that rows were selected on the same data; optimistic by construction")
            summary["tables"][name] = meta
            rep.append((name, sc, meta, tab))
            log(f"{name}: {meta['rows']} rows, {meta['n_eligible_patterns']}/{meta['n_candidate_patterns']} eligible, "
                f"{meta['n_replicated']} replicated, {meta['n_crowded_out']} crowded_out")
    write_json(out / "summary.json", summary)
    if version == "v4":
        decide(run, "subset-full-v4", "full-data S2 corpus tables v4 written (3 tables, no split, max 3 conditions)",
               "as v3 (no theme condition), max 3 conditions; 3-condition rows get their best 2-condition sub-rule, "
               "the delta of the third condition and a within-sub-rule permutation p")
    elif version == "v5":
        decide(run, "subset-full-v5", "full-data S2 emergency_referrals tables v5 written (3 tables, no split)",
               f"as the v2 theme tables, but the theme attributes come from the v5 theme run {theme_run} "
               "instead of run 4; run-4 step-7 rules are not a replication source; run-4 absence labels are not "
               "excluded (the v5 run maps absence wording to not_stated in step 4)")
    elif version == "v6":
        decide(run, "subset-full-v6", "full-data S2 emergency_referrals tables v6 written (3 tables, no split)",
               "as v5, but only the theme-run attributes are searched (no universal attribute); user request "
               "2026-10-29")
    elif version == "v2":
        decide(run, "subset-full-v2", "full-data S2 tables v2 written (9 tables, no split)",
               "not_stated and run-4 absence labels excluded; 10 rows; corpus support 40; run-4 attributes in "
               "emergency_referrals; previously confirmed rules appended as crowded_out")
    else:
        decide(run, "subset-full-v3", "full-data S2 corpus tables v3 written (3 tables, no split)",
               "as v2, but theme is not a rule attribute on the corpus tables; theme tables unchanged (v2)")
    write_report(out, summary, rep, col2name, set(r4_cols), version)


def write_report(out, summ, tables, col2name, r4, version="v2") -> None:
    rs = summ["replication_sources"]
    v5 = version in ("v5", "v6")
    head = ([f"# Subset S2 — full-data explanation tables, version 6 (emergency_referrals, v5 theme-run attributes only)\n",
             f"Corpus run `20261017T030528Z`, subset S2 (n = {summ['n_s2']}). No model call. Written {summ['started_at_utc']} (UTC).\n",
             f"**Version 6 = version 5 with only the {len(r4)} attributes of the v5 theme run `{summ['theme_run']}`** "
             "(columns marked `th:`); the seven universal attributes are not searched. Same settings as version 5. "
             "Previously confirmed rules use universal attributes, so they appear as crowded_out with reason "
             "\"attribute not in search\".\n"] if version == "v6" else
            [f"# Subset S2 — full-data explanation tables, version 5 (emergency_referrals, v5 theme run)\n",
             f"Corpus run `20261017T030528Z`, subset S2 (n = {summ['n_s2']}). No model call. Written {summ['started_at_utc']} (UTC).\n",
             f"**Version 5 = the version-2 emergency_referrals tables with the theme attributes of the v5 theme run "
             f"`{summ['theme_run']}`** (the corpus-run pipeline run inside the theme; columns marked `th:`) instead of the "
             "run-4 attributes. Same settings as version 2. The communication and corpus tables are not rebuilt.\n"] if v5 else
            ["# Subset S2 — full-data explanation tables, version 2\n",
             f"Corpus run `20261017T030528Z`, subset S2 (n = {summ['n_s2']}). No model call. Written {summ['started_at_utc']} (UTC). "
             "Version 1 is kept in `../full_tables/`.\n"] if version == "v2" else
            ["# Subset S2 — full-data explanation tables, version 4 (corpus, no theme condition, up to 3 conditions)\n",
             f"Corpus run `20261017T030528Z`, subset S2 (n = {summ['n_s2']}). No model call. Written {summ['started_at_utc']} (UTC).\n",
             "**Version 4 = version 3 with up to 3 conditions per rule.** Theme is not a rule attribute; `th≥10` is kept. "
             "Support ≥ 40, |effect| ≥ 0.05, up to 10 rows. Rules of up to 3 conditions confirmed earlier can now enter "
             "the search unless they need theme, a form attribute or an excluded value.\n",
             "**3-condition rows.** For each, the three 2-condition sub-rules are evaluated on the same items; the best "
             "one is the sub-rule with the largest deviation in the row's direction. `delta_pts` = deviation of the "
             "3-condition rule − deviation of that sub-rule (negative on a negative row = the third condition makes it "
             "worse). `kept` = share of the sub-rule's items the third condition keeps. `rest_pts` = deviation of the "
             "sub-rule items the third condition removes. `p_within` = permutation p (10,000) of the 3-condition items "
             "against random subsets of the same size drawn from inside the sub-rule. A small `p_within` means the third "
             "attribute picks out a different group; a large one means it only narrows the sub-rule. `p_within` is "
             "computed on the same data that chose the row and is optimistic.\n"] if version == "v4" else
            ["# Subset S2 — full-data explanation tables, version 3 (corpus, no theme condition)\n",
             f"Corpus run `20261017T030528Z`, subset S2 (n = {summ['n_s2']}). No model call. Written {summ['started_at_utc']} (UTC).\n",
             "**Version 3 changes one thing from version 2: theme is not a rule attribute on the corpus tables.** Rules "
             "use only the seven content attributes; `th≥10` (themes with at least 10 items in the slice) is kept. The "
             "theme tables are not rebuilt; they are in `../full_tables_v2/`. Previously confirmed rules that contain a "
             "theme condition can no longer enter the search and are appended as crowded_out with reason "
             "\"attribute not in search (theme)\".\n"])
    L = head + [
         "**These tables use all items of each scope, discovery and confirmation together.** They describe the data; "
         "they confirm nothing. `p_bh` is a permutation p (10,000) with Benjamini–Hochberg over the greedy rows of the "
         "table; it ignores that the rows were chosen on the same data, so it is optimistic. The only held-out evidence "
         "is `replicated`.\n",
         "**Changes from version 1.** `not_stated` is excluded from rules, together with unknown, not_applicable, "
         "parse_error, other and \"none of these\". " + (
             "The theme-run attributes need no extra absence labels: step 4 of the v5 pipeline already maps absence "
             "wording to not_stated (the run-4 labels are not excluded here, so \"no explicit request\" of requested "
             "help is an ordinary value). " if v5 else
             "On the run-4 attributes the five absence labels with the same meaning are excluded too: "
             + ", ".join(f"\"{v}\"" for v in summ["run4_absence_labels_excluded"]) + ". ") + "Up to 10 rows. "
         "Corpus support ≥ 40, theme support ≥ 20; |effect| ≥ 0.05 corpus, ≥ 0.08 theme. " + (
             f"emergency_referrals {'searches only' if version == 'v6' else 'also searches'} the {len(r4)} theme-run "
             "attributes (columns marked `th:`), joined by prompt_id.\n" if v5 else
             "emergency_referrals also searches the 14 run-4 attributes (columns marked `r4:`), joined by prompt_id "
             "(440 of 440 items annotated).\n"),
         "**Columns.** One column per attribute, `*` where the rule does not constrain it. `mean_gpt` / `mean_claude` are "
         "means of the table's target family (theme-centred `score_rel_*` on corpus tables, absolute `score_*` on theme "
         "tables). `dev_pts` = (rule mean − scope mean of the table's target) × 100; `dev_pct` = deviation / scope mean of "
         "the clipped score of the table's model. `ca_gpt` / `ca_claude` = context_awareness score in the slice / scope "
         "mean, on messages with a context_awareness criterion (`ca_n` of them in the slice); theme-centred on corpus "
         "tables, absolute on theme tables, unclipped. `worst_axis` follows step 7: per model, achieved points on the axis "
         "/ total positive points, theme-centred, slice minus scope, averaged over the two models; the axis with the "
         "largest term in the direction of the overall shift (`wa_pts` = that term × 100). `th≥10` = number of themes "
         "with at least 10 items in the slice.\n",
         f"**replicated** = the identical condition set was confirmed on a held-out split before: main run step 7 "
         f"({rs['main step 7']} rules), S2 run step 7 (corpus {rs['S2 step 7 corpus']}, emergency_referrals "
         f"{rs['S2 step 7 emergency_referrals']}, communication {rs['S2 step 7 communication']})" + (
             ". The theme run has no step 7, so no rule with a theme-run attribute can be replicated. " if v5 else
             f", run 4 step 7 ({rs['run 4 step 7']}, emergency_referrals). ") +
         "A theme-scope rule is read as its conditions plus "
         "`theme = <theme>`. Same conditions, not always the same population: the main run confirmed on all 4,027 items" +
         (".\n" if v5 else ", run 4 on all 444 emergency_referrals items.\n"),
         "**crowded_out rows** (below the separator) are previously confirmed rules that apply to the scope but are not "
         "in the table, with their stats on this scope and the `reason`. \"eligible, not selected by greedy\" means the "
         "greedy search passed them over. Any other reason means the rule could not enter this search at all. Their p "
         "is the raw permutation p (`p_perm`), not BH-adjusted.\n"]
    if version in ("v3", "v4"):
        L = [x.replace("**Changes from version 1.**", "**Settings inherited from version 2.**") for x in L]
    for name, sc, meta, tab in tables:
        scope = "corpus S2" if sc["theme"] is None else f"theme {sc['theme']}"
        L.append(f"## {scope} — target `{meta['target']}`\n")
        L.append(f"n = {meta['n']}, scope mean {meta['scope_mean_target']:.4f} (clipped score mean {meta['scope_mean_clipped']:.4f}); "
                 f"support ≥ {meta['min_support']}, |effect| ≥ {meta['min_effect']}; {meta['n_eligible_patterns']} of "
                 f"{meta['n_candidate_patterns']} patterns eligible; {meta['rows']} rows, {meta['n_replicated']} replicated, "
                 f"{meta['n_crowded_out']} crowded_out.\n")
        base = tab[tab.row_type == "baseline"]
        g = tab[tab.row_type == "greedy"].sort_values("dev_pts")
        co = tab[tab.row_type == "crowded_out"].sort_values("dev_pts")
        t = pd.concat([base, g, co])
        show = pd.DataFrame({"row": [("base" if r.row_type == "baseline" else f"#{int(r.step)}" if r.row_type == "greedy"
                                      else "crowded_out") for r in t.itertuples()]})
        for c in sc["cols"]:
            show[(("th:" if v5 else "r4:") if c in r4 else "") + c] = t[c].fillna("*").to_numpy()
        show["n"] = t.n.to_numpy()
        show["mean_gpt"] = [f"{v:.3f}" for v in t.mean_gpt]
        show["mean_claude"] = [f"{v:.3f}" for v in t.mean_claude]
        show["dev_pts"] = [f"{v:+.1f}" for v in t.dev_pts]
        show["dev_pct"] = [f"{v:+.1f}" for v in t.dev_pct]
        show["p_bh"] = ["" if pd.isna(v) else f"{v:.4f}" for v in t.p_bh]
        show["p_perm"] = ["" if pd.isna(v) else f"{v:.4f}" for v in t.p_perm]
        show["ca_gpt"] = [f"{a:.2f} / {b:.2f}" for a, b in zip(t.ca_gpt_slice, t.ca_gpt_scope)]
        show["ca_claude"] = [f"{a:.2f} / {b:.2f}" for a, b in zip(t.ca_claude_slice, t.ca_claude_scope)]
        show["ca_n"] = t.ca_n_slice.to_numpy()
        show["worst_axis"] = t.worst_axis.fillna("").to_numpy()
        show["wa_pts"] = ["" if pd.isna(v) else f"{v:+.1f}" for v in t.worst_axis_pts]
        show["wa_n"] = t.worst_axis_n.to_numpy()
        show["th≥10"] = t.themes_ge10.to_numpy()
        show["replicated"] = t.replicated.astype(str).replace("", "").to_numpy()
        show["reason"] = t.reason.fillna("").to_numpy()
        L.append(md(show))
        if "sub_rule" in t.columns and t.sub_rule.notna().any():
            t3 = t[t.sub_rule.notna()]
            L.append("**3-condition rows: best 2-condition sub-rule**\n")
            L.append(md(pd.DataFrame({
                "row": ["#" + str(int(r.step)) if r.row_type == "greedy" else "crowded_out" for r in t3.itertuples()],
                "rule": [r.rule_columns.replace(" AND ", " ∧ ") for r in t3.itertuples()],
                "n": t3.n.to_numpy(), "dev_pts": [f"{v:+.1f}" for v in t3.dev_pts],
                "best sub-rule": [r.sub_rule.replace(" AND ", " ∧ ") for r in t3.itertuples()],
                "sub_n": t3.sub_n.astype(int).to_numpy(), "sub_dev_pts": [f"{v:+.1f}" for v in t3.sub_dev_pts],
                "third condition": t3.third_condition.to_numpy(), "delta_pts": [f"{v:+.1f}" for v in t3.delta_pts],
                "kept": [f"{v:.2f}" for v in t3.kept_share], "rest_pts": [f"{v:+.1f}" for v in t3.rest_of_sub_dev_pts],
                "sub passes support/effect": [f"{bool(a)}/{bool(b)}" for a, b in zip(t3.sub_meets_support, t3.sub_meets_effect)],
                "p_within": [f"{v:.4f}" for v in t3.p_third_within_sub]})))
        rr = t[(t.replicated == True)]  # noqa: E712
        if len(rr):
            L.append("Replication sources: " + "; ".join(
                f"{'#' + str(int(r.step)) if r.row_type == 'greedy' else 'crowded_out ' + r.rule_columns} ← {r.replicated_in}"
                for r in rr.itertuples()) + "\n")
    (out / f"REPORT_full_tables_{version}.md").write_text("\n".join(L))
    log(f"report written: {out / f'REPORT_full_tables_{version}.md'}")


if __name__ == "__main__":
    run(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "v2")
