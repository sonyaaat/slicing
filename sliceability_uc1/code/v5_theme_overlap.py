"""Redundancy of a theme run's attributes against the corpus run's universal attributes.

Curation (step 5) compares attributes only inside one run. In a theme scope the slice search
uses both sets, so this checks every (theme attribute, universal attribute) pair with the
curation rule: Cramer's V on the items where both have a value (not_applicable, unknown and
parse_error do not count; not_stated and other do), on all items of the theme, flagged when
V >= curation.max_cramers_v. Annotation is label-blind, so this reads no score. Nothing is
dropped here; the flags are for a decision.

    .venv/bin/python sliceability_uc1/code/v5_theme_overlap.py <theme_run_dir>
Writes <theme_run_dir>/theme_vs_universal_cramers_v.csv.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import NA, PARSE_ERROR, UNKNOWN, UC1_ROOT, Run, die, log, write_meta  # noqa: E402
from step5_curate import cramers_v  # noqa: E402
from v5_subset import ATTRS  # noqa: E402

UNCOVERED = (NA, UNKNOWN, PARSE_ERROR)


def run(run_dir: Path) -> pd.DataFrame:
    run = Run(run_dir)
    src = UC1_ROOT / run.cfg["data"]["reuse_from"]
    th = run.cfg["data"]["theme"]
    fin = json.loads(run.path("attributes_final.json").read_text())["attributes"]
    uni = pd.read_csv(src / "annotations_full.csv", keep_default_na=False)
    uni = uni[uni.theme == th].set_index("prompt_id")[ATTRS]
    own = pd.read_csv(run.path("annotations_full.csv"), keep_default_na=False).set_index("prompt_id")
    if set(own.index) != set(uni.index):
        die(f"item sets differ: theme run {len(own)}, corpus run theme rows {len(uni)}")
    vmax = run.cfg["curation"]["max_cramers_v"]
    rows = []
    for a in fin:
        x = own[a["column"]]
        for u in ATTRS:
            y = uni.loc[x.index, u]
            ok = ~x.isin(UNCOVERED) & ~y.isin(UNCOVERED)
            v = cramers_v(x[ok], y[ok]) if ok.sum() >= 10 else float("nan")
            rows.append({"theme_attribute": a["name"], "universal_attribute": u, "n_both": int(ok.sum()),
                         "cramers_v": v, "flag": bool(v >= vmax)})
    out = pd.DataFrame(rows).sort_values("cramers_v", ascending=False)
    p = run.path("theme_vs_universal_cramers_v.csv")
    out.to_csv(p, index=False)
    write_meta(run, p, "overlap", universal_from=run.cfg["data"]["reuse_from"], items=int(len(own)),
               threshold=vmax, api_calls=0)
    log(f"{int(out.flag.sum())} pair(s) with V >= {vmax} of {len(out)}")
    return out


if __name__ == "__main__":
    print(run(Path(sys.argv[1])).to_string(index=False))
