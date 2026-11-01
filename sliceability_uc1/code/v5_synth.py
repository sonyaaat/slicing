"""Step 8A of the v5 corpus run - synthetic check of the slicing step (no LLM).

On the full annotation (all 4,027 messages, no split: the planted truth is known), pick 10
groups "attribute = value" among the final attributes, subtract delta from the target of
every message in the group, and build the explanation table (2 conditions, the step-6
parameters, theme allowed). 10 groups x 3 deltas = 30 tables.

Group choice (seed 42): values not excluded from rules, with >= min_group_support items and
<= max_group_share of the corpus; shuffled; first one value per attribute, then a second
pass, until 10.

Per test:
  hit_top3_exact     the planted single condition is one of the first 3 rows
  hit_top3_contains  a row among the first 3 contains the planted condition
  rank_exact         position of the planted single-condition row (None if absent)
  n_rows, n_rows_planted (rows containing the planted condition),
  n_spurious         rows that neither contain the planted condition nor appear in the
                     unplanted (delta = 0) table
  precision          n_rows_planted / (n_rows_planted + n_spurious)

The delta = 0 table is built on all 4,027 real targets, which include the confirmation
split. It is used only to tell spurious rows from rows that are already there, is never
written to disk, and no row of it is reported. preregistered_rules.json must exist first.
"""

from __future__ import annotations

import random

import numpy as np
import pandas as pd

from common import Run, die, log, read_json, write_json, write_meta
from v5_data import load_data
from v5_infra import decide
from v5_tables import column_target, search


def run(run: Run) -> None:
    if not run.path(run.cfg["prereg"]["file"]).exists():
        die("synthetic A reads all 4,027 targets; preregistered_rules.json must be written first")
    sc = run.cfg["synthetic"]["level_a"]
    ec = run.cfg["et"]
    fin = read_json(run.path("attributes_final.json"))["attributes"]
    wide = pd.read_csv(run.path("annotations_full.csv"))
    df = load_data(run)
    tgt = column_target(run, "mean")
    data = df[["prompt_id", tgt]].merge(wide, on="prompt_id").sort_values("prompt_id").reset_index(drop=True)
    data = data[data[tgt].notna()].reset_index(drop=True)
    cols = [a["column"] for a in fin if not a.get("excluded_from_et")] + (["theme"] if ec["allow_theme"] else [])
    N = len(data)
    excl = set(ec["exclude_values"])
    elig = []
    for a in fin:
        if a.get("excluded_from_et"):
            continue
        vc = data[a["column"]].astype(str).value_counts()
        for v, k in vc.items():
            if v not in excl and sc["min_group_support"] <= k <= sc["max_group_share"] * N:
                elig.append((a["column"], v, int(k)))
    rng = random.Random(sc["seed"])
    rng.shuffle(elig)
    groups, used = [], set()
    for pas in (1, 2, 3):
        for c, v, k in elig:
            if len(groups) >= sc["groups"]:
                break
            if (c, v) in [(g[0], g[1]) for g in groups]:
                continue
            if pas == 1 and c in used:
                continue
            groups.append((c, v, k)); used.add(c)
    if len(groups) < sc["groups"]:
        decide(run, "8A", f"{len(groups)} groups instead of {sc['groups']}",
               f"only {len(elig)} eligible attribute values")
    kw = dict(max_conj=ec["max_conj"], min_support=ec["min_support"], min_effect=ec["min_effect"],
              max_rows=ec["max_rows"], exclude=ec["exclude_values"])
    base, _, _, _ = search(data, cols, tgt, **kw)
    base_pats = {tuple(sorted(r["pattern"])) for r in base["rows"]}
    rows = []
    for c, v, k in groups:
        g = (data[c].astype(str) == v).to_numpy()
        for delta in sc["deltas"]:
            d2 = data.copy()
            d2.loc[g, tgt] = d2.loc[g, tgt] - delta
            res, _, _, _ = search(d2, cols, tgt, **kw)
            pats = [tuple(r["pattern"]) for r in res["rows"]]
            planted = (c, v)
            exact = [i + 1 for i, p in enumerate(pats) if p == (planted,)]
            contains = [planted in p for p in pats]
            spurious = sum(1 for p, ct in zip(pats, contains)
                           if not ct and tuple(sorted(p)) not in base_pats)
            n_pl = sum(contains)
            rows.append({"group_attribute": c, "group_value": v, "group_support": k,
                         "group_share": k / N, "delta": delta,
                         "hit_top3_exact": bool(exact and exact[0] <= 3),
                         "hit_top3_contains": any(contains[:3]),
                         "rank_exact": exact[0] if exact else None, "n_rows": len(pats),
                         "n_rows_planted": n_pl, "n_spurious": spurious,
                         "precision": n_pl / (n_pl + spurious) if (n_pl + spurious) else np.nan})
        log(f"8A: {c} = {v} (n={k}) done")
    out = pd.DataFrame(rows)
    out.to_csv(run.path("synthetic_a.csv"), index=False)
    summ = out.groupby("delta").agg(recall_at3_exact=("hit_top3_exact", "mean"),
                                    recall_at3_contains=("hit_top3_contains", "mean"),
                                    precision_mean=("precision", "mean"),
                                    spurious_mean=("n_spurious", "mean")).reset_index()
    write_json(run.path("synthetic_a_summary.json"),
               {"target": tgt, "n": N, "baseline_rows": len(base["rows"]),
                "by_delta": summ.to_dict("records")})
    write_meta(run, run.path("synthetic_a.csv"), "8A", n_tests=len(out), target=tgt,
               note="delta=0 baseline used only to classify spurious rows; not written")
    log("8A summary:\n" + summ.to_string(index=False))
