"""Full-data explanation tables on subset S2 of a v5 corpus run. No model call.

Tables are built on ALL S2 items of each scope (no split): they are descriptive. Their
permutation p ignores that rows were selected on the same data and is optimistic by
construction. The only held-out evidence is the `replicated` column: True if the identical
rule was confirmed on a held-out split in an earlier check.

Scopes: corpus S2 (score_rel_gpt / _claude / _mean, theme allowed, support >= 60, |effect|
>= 0.05); theme emergency_referrals and communication (score_gpt / _claude / _mean, theme not
an attribute, support >= 20, |effect| >= 0.08). Max 2 conditions, up to 8 rows, the greedy
information-gain search of v5_tables.search, permutation p (10,000, seed 42 + step) with BH
over the rows of each table.

Rule identity for `replicated`: the set of attribute=value conditions, with a theme-scope
rule read as the same conditions plus theme = <its theme>. Sources: main run step 7
(FINAL_TABLE_CORPUS.csv), S2 run step 7 (subset_s2/FINAL_TABLE_*.csv), run 4 step 7
(runs/20261016T235755Z/FINAL_TABLE_UC1.csv, emergency_referrals partition).
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
from v5_infra import decide, utcnow  # noqa: E402
from v5_subset import ATTRS, EXCLUDE_VALUES, NONAPPL, TRIPLE, md  # noqa: E402
from v5_tables import mask_of, search  # noqa: E402

MODELS = ("gpt", "claude", "mean")
SCOPES = [
    {"key": "corpus", "theme": None, "family": "score_rel", "cols": ATTRS + ["theme"],
     "min_support": 60, "min_effect": 0.05},
    {"key": "theme_emergency_referrals", "theme": "emergency_referrals", "family": "score", "cols": ATTRS,
     "min_support": 20, "min_effect": 0.08},
    {"key": "theme_communication", "theme": "communication", "family": "score", "cols": ATTRS,
     "min_support": 20, "min_effect": 0.08},
]
MAX_CONJ, MAX_ROWS, PERM_N, PERM_SEED = 2, 8, 10000, 42
RUN4 = "20261016T235755Z"


def key_of(conds, theme=None) -> frozenset:
    s = {(a, v) for a, v in conds}
    if theme is not None:
        s.add(("theme", theme))
    return frozenset(s)


def conds_of(rule_columns: str):
    return [tuple(x.split("=", 1)) for x in rule_columns.split(" AND ")]


def confirmed_sources(run: Run) -> tuple[dict, dict]:
    """key -> list of 'source (scope)' for every rule confirmed on a held-out split."""
    src: dict[frozenset, list[str]] = {}
    files = {"main step 7": [(run.path("FINAL_TABLE_CORPUS.csv"), None, "corpus")]}
    files["S2 step 7"] = [(run.path("subset_s2/FINAL_TABLE_corpus.csv"), None, "S2 corpus")] + [
        (run.path(f"subset_s2/FINAL_TABLE_theme_{t}.csv"), t, f"S2 {t}") for t in ("emergency_referrals", "communication")]
    files["run 4 step 7"] = [(RUNS_DIR / RUN4 / "FINAL_TABLE_UC1.csv", "emergency_referrals", "run 4 emergency_referrals")]
    counts = {}
    for label, lst in files.items():
        n = 0
        for f, theme, scope in lst:
            if not f.exists():
                die(f"{f} missing")
            ft = pd.read_csv(f)
            for rc in ft.rule_columns:
                src.setdefault(key_of(conds_of(rc), theme), []).append(f"{label} ({scope})")
                n += 1
        counts[label] = n
    return src, counts


def run(run_dir: Path) -> None:
    run = Run(run_dir)
    out = run.path("subset_s2/full_tables")
    if out.exists() and any(out.iterdir()):
        die(f"{out} is not empty")
    out.mkdir(parents=True, exist_ok=True)
    t0 = utcnow()

    df = pd.read_csv(run.path("corpus_data.csv"))
    ann = pd.read_csv(run.path("annotations_full.csv"), keep_default_na=False)
    full = df.merge(ann.drop(columns="theme"), on="prompt_id").sort_values("prompt_id").reset_index(drop=True)
    n_app = sum((~full[c].isin(NONAPPL)).astype(int) for c in TRIPLE)
    s2 = full[n_app >= 2].reset_index(drop=True)
    rec = run.cfg.get("subset_s2", {})
    if len(s2) != 3077 or rec.get("n") != len(s2):
        die(f"S2 has {len(s2)} items; run_config subset_s2.n = {rec.get('n')}")
    fin = json.loads(run.path("attributes_final.json").read_text())["attributes"]
    col2name = {a["column"]: a["name"] for a in fin} | {"theme": "theme"}
    src, src_counts = confirmed_sources(run)
    log(f"S2 {len(s2)} items; confirmed rules loaded: {src_counts}")

    summary = {"started_at_utc": t0, "n_s2": len(s2), "split_used": "none (all items of the scope)",
               "replication_sources": src_counts, "params": {"max_conj": MAX_CONJ, "max_rows": MAX_ROWS,
               "permutation_n": PERM_N, "permutation_seed": PERM_SEED, "exclude_values": EXCLUDE_VALUES,
               "scopes": [{k: v for k, v in s.items()} for s in SCOPES]}, "tables": {}}
    report_tables = []
    for sc in SCOPES:
        data = s2 if sc["theme"] is None else s2[s2.theme == sc["theme"]].reset_index(drop=True)
        clip_mean = {m: float(data[f"score_{m}"].mean()) for m in MODELS}
        for m in MODELS:
            tgt = f"{sc['family']}_{m}"
            res, ok, lo, hi = search(data, sc["cols"], tgt, max_conj=MAX_CONJ, min_support=sc["min_support"],
                                     min_effect=sc["min_effect"], max_rows=MAX_ROWS, exclude=EXCLUDE_VALUES)
            sub = data[ok].reset_index(drop=True)
            y = sub[tgt].to_numpy(float)
            fam_g, fam_c = sub[f"{sc['family']}_gpt"], sub[f"{sc['family']}_claude"]
            rows, pv = [], []
            base = {c: "*" for c in sc["cols"]}
            rows.append({"step": 0, **base, "n": len(sub), "mean_gpt": float(fam_g.mean()),
                         "mean_claude": float(fam_c.mean()), "abs_mean_gpt": float(sub.score_gpt.mean()),
                         "abs_mean_claude": float(sub.score_claude.mean()), "dev_pts": 0.0, "dev_pct": 0.0,
                         "p_perm": np.nan, "p_bh": np.nan, "replicated": "", "replicated_in": "",
                         "rule_columns": "(all items)"})
            for r in res["rows"]:
                mk = mask_of(sub, r["pattern"])
                p = permutation_p(y, mk, PERM_N, PERM_SEED + r["step"])
                pv.append(p)
                dev = float(y[mk].mean() - y.mean())
                hits = src.get(key_of(r["pattern"], sc["theme"]), [])
                rows.append({"step": r["step"], **base, **{a: v for a, v in r["pattern"]}, "n": int(mk.sum()),
                             "mean_gpt": float(fam_g[mk].mean()), "mean_claude": float(fam_c[mk].mean()),
                             "abs_mean_gpt": float(sub.score_gpt[mk].mean()),
                             "abs_mean_claude": float(sub.score_claude[mk].mean()),
                             "dev_pts": 100 * dev, "dev_pct": 100 * dev / clip_mean[m], "p_perm": p, "p_bh": np.nan,
                             "replicated": bool(hits), "replicated_in": "; ".join(sorted(set(hits))),
                             "rule_columns": " AND ".join(f"{a}={v}" for a, v in r["pattern"])})
            for row, a in zip(rows[1:], bh(pv)):
                row["p_bh"] = a
            tab = pd.DataFrame(rows)
            name = f"et_full_{sc['key']}_{m}"
            f = out / f"{name}.csv"
            tab.to_csv(f, index=False)
            meta = {"scope": sc["key"], "target": tgt, "n": len(sub), "scope_mean_target": float(y.mean()),
                    "scope_mean_clipped": clip_mean[m], "rescale_range": [lo, hi],
                    "n_candidate_patterns": res["n_candidates"], "n_eligible_patterns": res["n_eligible"],
                    "min_support": sc["min_support"], "min_effect": sc["min_effect"], "rows": len(rows) - 1,
                    "n_replicated": int(sum(r["replicated"] is True for r in rows[1:]))}
            write_meta(run, f, "subset-full", api_calls=0, **meta, split="none: all S2 items of the scope",
                       note="p ignores that rows were selected on the same data; optimistic by construction")
            summary["tables"][name] = meta
            report_tables.append((name, sc, meta, tab))
            log(f"{name}: {meta['rows']} rows, {meta['n_eligible_patterns']}/{meta['n_candidate_patterns']} eligible, "
                f"{meta['n_replicated']} replicated")
    write_json(out / "summary.json", summary)
    decide(run, "subset-full", "full-data S2 tables written (9 tables, no split)",
           "descriptive tables on all S2 items; held-out evidence only via the replicated column")
    write_report(out, summary, report_tables, col2name)


def write_report(out: Path, summ: dict, tables, col2name) -> None:
    L = ["# Subset S2 — full-data explanation tables\n",
         f"Corpus run `20261017T030528Z`, subset S2 (n = {summ['n_s2']}). No model call. Written {summ['started_at_utc']} (UTC).\n",
         "**These tables use all items of each scope, discovery and confirmation together.** They describe the "
         "data; they confirm nothing. `p_bh` is a permutation p (10,000) with Benjamini–Hochberg over the rows of "
         "the table, and it ignores that the rows were chosen on the same data, so it is optimistic. The only "
         "held-out evidence is `replicated`.\n",
         "**Columns.** One column per attribute (and theme on corpus tables), `*` where the rule does not constrain it. "
         "`mean_gpt` / `mean_claude` are means of the table's target family (theme-centred `score_rel_*` on corpus tables, "
         "absolute `score_*` on theme tables). `dev_pts` = (rule mean − scope mean of the table's target) × 100. "
         "`dev_pct` = deviation / scope mean of the clipped score of the table's model. Row 0 is the scope baseline. "
         "Rows are sorted worst first; `step` is the greedy order.\n",
         "**replicated** = the identical condition set was confirmed on a held-out split in an earlier check: main run "
         f"step 7 ({summ['replication_sources']['main step 7']} confirmed rules), S2 run step 7 "
         f"({summ['replication_sources']['S2 step 7']}), run 4 step 7 ({summ['replication_sources']['run 4 step 7']}). "
         "A theme-scope rule is read as its conditions plus `theme = <theme>`. Run 4 used its own attribute "
         "vocabulary (prompt_form, severity_wording, …), which shares no attribute with the universal set, so no "
         "run-4 rule can match. The main run confirmed on all 4,027 items, the S2 run on S2 only; a match means the "
         "same conditions, not the same population.\n"]
    for name, sc, meta, tab in tables:
        scope = "corpus S2" if sc["theme"] is None else f"theme {sc['theme']}"
        L.append(f"## {scope} — target `{meta['target']}`\n")
        L.append(f"n = {meta['n']}, scope mean {meta['scope_mean_target']:.4f} (clipped score mean "
                 f"{meta['scope_mean_clipped']:.4f}); support ≥ {meta['min_support']}, |effect| ≥ {meta['min_effect']}; "
                 f"{meta['n_eligible_patterns']} of {meta['n_candidate_patterns']} patterns eligible; {meta['rows']} rows, "
                 f"{meta['n_replicated']} replicated.\n")
        t = pd.concat([tab.iloc[:1], tab.iloc[1:].sort_values("dev_pts")])
        show = t[["step"] + sc["cols"] + ["n", "mean_gpt", "mean_claude", "dev_pts", "dev_pct", "p_bh", "replicated"]].copy()
        show = show.rename(columns={c: col2name[c].replace(" ", "_") if c != "theme" else c for c in sc["cols"]})
        for c in ("mean_gpt", "mean_claude"):
            show[c] = show[c].map(lambda v: f"{v:.3f}")
        for c in ("dev_pts", "dev_pct"):
            show[c] = show[c].map(lambda v: f"{v:+.1f}")
        show["p_bh"] = show["p_bh"].map(lambda v: "" if pd.isna(v) else f"{v:.4f}")
        L.append(md(show))
        rep = t[t.replicated == True]  # noqa: E712
        if len(rep):
            L.append("Replicated rows: " + "; ".join(f"step {int(r.step)} ← {r.replicated_in}" for r in rep.itertuples()) + "\n")
    (out / "REPORT_full_tables.md").write_text("\n".join(L))
    log(f"report written: {out / 'REPORT_full_tables.md'}")


if __name__ == "__main__":
    run(Path(sys.argv[1]))
