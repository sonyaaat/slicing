#!/usr/bin/env python3
"""Write demo/data/test_expected.json: the greedy rows of the full-data explanation tables the
paper reports (subset_s2/full_tables_v2, _v3, _v4, _v5, _v6), for demo/tests/check_et.mjs. The v2
emergency_referrals tables used the run-4 theme attributes, which the demo no longer loads; the
emergency_referrals tables come from v5 (theme attributes of the v5 theme run).

    .venv/bin/python demo/tests/make_expected.py && node demo/tests/check_et.mjs
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
S2 = ROOT / "sliceability_uc1/runs/20261017T030528Z/subset_s2"
ATTRS = ["patient_age", "episode_timing", "possible_trigger", "care_setting", "symptom_course",
         "intervention_type", "evidence_basis"]

cases = []
for ver in ("v2", "v3", "v4", "v5", "v6"):
    d = S2 / f"full_tables_{ver}"
    summ = json.loads((d / "summary.json").read_text())
    for name, meta in summ["tables"].items():
        tab = pd.read_csv(d / f"{name}.csv", keep_default_na=False)
        g = tab[tab.row_type == "greedy"]
        scope = meta["scope"]
        if ver == "v2" and scope == "theme_emergency_referrals":
            continue
        theme = None if scope == "corpus" else scope.replace("theme_", "")
        attr_cols = [c for c in tab.columns[:tab.columns.get_loc("n")] if c not in ("row_type", "step")]
        rows = []
        for r in g.itertuples():
            conds = [[a, v] for a, v in (x.split("=", 1) for x in r.rule_columns.split(" AND "))]
            rows.append({"step": int(float(r.step)), "conds": conds, "n": int(float(r.n)), "dev_pts": float(r.dev_pts)})
        cases.append({"version": ver, "table": name, "theme": theme, "target": meta["target"],
                      "cols": attr_cols, "min_support": meta["min_support"], "min_effect": meta["min_effect"],
                      "max_conj": 3 if ver == "v4" else 2, "max_rows": 10,
                      "n": meta["n"], "n_candidates": meta["n_candidate_patterns"],
                      "n_eligible": meta["n_eligible_patterns"], "rows": rows})
out = ROOT / "demo/data/test_expected.json"
out.write_text(json.dumps(cases, indent=1))
print(f"{len(cases)} tables -> {out.relative_to(ROOT)}")
