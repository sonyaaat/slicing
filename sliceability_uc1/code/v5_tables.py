"""Step 6 (full annotation + explanation tables) and the preregistration of the v5 corpus run.

Full annotation: final attributes on all 4,027 messages, primary model and seed (the 300
sample items are cache hits). Values with < curation.min_support_full items on the corpus
are folded into other (annotation is label-blind, so counting on all 4,027 reads no score).

Tables: discovery split only. Target family from step 0 (e.g. score_rel): tables gpt /
claude / mean / diff use <family>_gpt / _claude / _mean / _diff, each with 2 and 3
conditions. Theme is an extra attribute. Excluded from rules: unknown, not_applicable,
other, none of these, parse_error; not_stated is allowed. The search is et.fit_table's
algorithm (greedy information gain over a max-entropy model) on the target rescaled to
[0, 1] with the discovery min/max; every reported number is in the target's own units.

Preregistration: config prereg.rule, written with a UTC timestamp before anything reads
the confirmation split. Nothing here reads it.
"""

from __future__ import annotations

import hashlib
import itertools
from collections import Counter

import numpy as np
import pandas as pd

from common import OTHER, PARSE_ERROR, Run, die, log, read_json, write_json, write_meta
from et import _bern_kl, _fit, _total_ce, bh, permutation_p
from v5_curate import annotate_grid, mapped
from v5_data import load_data
from v5_infra import V5LLM, decide, utcnow


def column_target(run: Run, model: str) -> str:
    return f"{run.cfg['target_family']}_{model}"


def fit_table(values: dict[str, np.ndarray], y: np.ndarray, *, max_conj: int, min_support: int,
              min_effect: float, max_rows: int, exclude=frozenset(), ridge=1e-6, min_gain=1e-9) -> dict:
    """et.fit_table with candidate masks built as booleans and pre-filtered by support, so
    3-condition searches over ~10 attributes fit in memory. Same selection rule."""
    n = len(y)
    gmean = float(y.mean())
    attrs = list(values)
    doms = {a: sorted(set(values[a].tolist()) - set(exclude), key=str) for a in attrs}
    single = {(a, v): values[a] == v for a in attrs for v in doms[a]}
    single = {k: m for k, m in single.items() if m.sum() >= min_support}
    pats, masks = [], []
    n_cand = 0
    for k in range(1, max_conj + 1):
        for combo in itertools.combinations(attrs, k):
            lists = [[(a, v) for v in doms[a] if (a, v) in single] for a in combo]
            for conds in itertools.product(*lists):
                n_cand += 1
                mk = single[conds[0]].copy()
                for c in conds[1:]:
                    mk &= single[c]
                s = int(mk.sum())
                if s < min_support:
                    continue
                if abs(float(y[mk].mean()) - gmean) < min_effect:
                    continue
                pats.append(tuple(conds)); masks.append(mk)
    if not pats:
        return {"rows": [], "global_mean": gmean, "n": n, "n_candidates": n_cand, "n_eligible": 0}
    M = np.array(masks, dtype=float)
    sup = M.sum(axis=1)
    obs = (M @ y) / sup
    rows, sel, beta = [], [], None
    u = np.full(n, gmean)
    taken = np.zeros(len(pats), dtype=bool)
    for step in range(1, max_rows + 1):
        est = (M @ u) / sup
        gain = sup * _bern_kl(obs, est)
        gain[taken] = -np.inf
        i = int(np.argmax(gain))
        if not np.isfinite(gain[i]) or gain[i] < min_gain:
            break
        taken[i] = True
        sel.append(i)
        X = np.column_stack([np.ones(n)] + [M[j] for j in sel])
        beta, u = _fit(y, X, ridge, beta)
        rows.append({"step": step, "pattern": pats[i], "support": int(sup[i]), "mean": float(obs[i]),
                     "estimate_before": float(est[i]), "gain": float(gain[i]),
                     "cross_entropy_after": _total_ce(y, u)})
    return {"rows": rows, "global_mean": gmean, "n": n, "n_candidates": n_cand,
            "n_eligible": len(pats)}


def read_et(path) -> pd.DataFrame:
    """et_*.csv; a table with no row is written with its header only (see step6)."""
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=["step", "rule", "rule_columns", "support", "deviation",
                                     "deviation_gpt", "deviation_claude", "deviation_mean"])


def rule_text(pattern, col2name) -> str:
    return " AND ".join(f"{col2name[a]} = {v}" for a, v in pattern)


def search(data: pd.DataFrame, cols: list[str], target: str, *, max_conj: int, min_support: int,
           min_effect: float, max_rows: int, exclude) -> tuple[dict, np.ndarray, float, float]:
    ok = data[target].notna().to_numpy()
    sub = data[ok].reset_index(drop=True)
    y_raw = sub[target].to_numpy(float)
    lo, hi = float(y_raw.min()), float(y_raw.max())
    y = (y_raw - lo) / (hi - lo)
    vals = {c: sub[c].astype(str).to_numpy() for c in cols}
    res = fit_table(vals, y, max_conj=max_conj, min_support=min_support,
                    min_effect=min_effect / (hi - lo), max_rows=max_rows, exclude=frozenset(exclude))
    return res, ok, lo, hi


def mask_of(df: pd.DataFrame, pattern) -> np.ndarray:
    m = np.ones(len(df), dtype=bool)
    for a, v in pattern:
        m &= (df[a].astype(str) == v).to_numpy()
    return m


def full_annotation(run: Run) -> tuple[pd.DataFrame, list[dict]]:
    fj = read_json(run.path("attributes_final.json"))
    fin = fj["attributes"]
    df = load_data(run).sort_values("prompt_id").reset_index(drop=True)
    text = dict(zip(df.prompt_id, df.user_text))
    llm = V5LLM(run, "annotation")
    long = annotate_grid(run, llm, fin, df.prompt_id.tolist(), text, run.cfg["annotation"]["seed"], "6")
    vm = {a["name"]: a["value_map"] for a in fin}
    long["value_final"] = [mapped(pd.Series([v]), vm[a]).iloc[0] for v, a in zip(long.value, long.attribute)]
    min_full = run.cfg["curation"]["min_support_full"]
    for a in fin:
        sel = long.attribute == a["name"]
        cnt = Counter(long.loc[sel, "value_final"])
        meaningful = [v for v in a["values"] if v != OTHER]
        fold = [v for v in meaningful if cnt.get(v, 0) < min_full]
        a["folded_full"] = fold
        a["values_final"] = [v for v in meaningful if v not in fold] + [OTHER]
        a["value_counts_full"] = {k: int(v) for k, v in cnt.items()}
        long.loc[sel & long.value_final.isin(fold), "value_final"] = OTHER
        if fold:
            decide(run, "6", f"'{a['name']}': {fold} folded into other",
                   f"< {min_full} items on all {len(df):,} messages")
        if len(a["values_final"]) - 1 < 2:
            decide(run, "6", f"'{a['name']}' excluded from the table search",
                   "fewer than 2 values after the full-corpus refold")
            a["excluded_from_et"] = True
    write_json(run.path("attributes_final.json"), fj)
    write_meta(run, run.path("attributes_final.json"), "5+6", n_final=len(fin),
               note="values_final / folded_full added by step 6")
    long = long.merge(df[["prompt_id", "theme"]], on="prompt_id")
    long.to_csv(run.path("annotations_full_long.csv"), index=False)
    wide = long.pivot(index="prompt_id", columns="attribute", values="value_final")
    wide = wide.rename(columns={a["name"]: a["column"] for a in fin}).reset_index()
    wide = df[["prompt_id", "theme"]].merge(wide, on="prompt_id")
    wide.to_csv(run.path("annotations_full.csv"), index=False)
    write_meta(run, run.path("annotations_full.csv"), "6", model=llm.model, n_items=len(wide),
               n_attributes=len(fin), n_parse_error=int((long.value == PARSE_ERROR).sum()))
    log(f"6: annotations_full.csv {wide.shape}; parse errors {int((long.value == PARSE_ERROR).sum())}")
    return wide, fin


def step6(run: Run) -> None:
    wide, fin = full_annotation(run)
    ec = run.cfg["et"]
    df = load_data(run)
    sp = pd.read_csv(run.path("split_corpus.csv"))
    disc_ids = set(sp.loc[sp.split == "discovery", "prompt_id"])
    data = df[df.prompt_id.isin(disc_ids)].merge(wide.drop(columns="theme"), on="prompt_id")
    data = data.sort_values("prompt_id").reset_index(drop=True)
    cols = [a["column"] for a in fin if not a.get("excluded_from_et")] + (["theme"] if ec["allow_theme"] else [])
    col2name = {a["column"]: a["name"] for a in fin} | {"theme": "theme"}
    axes = run.cfg["data"]["axes"]
    fam = run.cfg["target_family"]
    for spec in ec["tables"]:
        tgt = column_target(run, spec["model"])
        eff = ec["diff_min_effect"] if spec["model"] == "diff" else ec["min_effect"]
        res, ok, lo, hi = search(data, cols, tgt, max_conj=spec["max_conj"], min_support=ec["min_support"],
                                 min_effect=eff, max_rows=ec["max_rows"], exclude=ec["exclude_values"])
        sub = data[ok].reset_index(drop=True)
        y = sub[tgt].to_numpy(float)
        rows, pv = [], []
        for r in res["rows"]:
            mk = mask_of(sub, r["pattern"])
            p = permutation_p(y, mk, ec["permutation_n"], ec["permutation_seed"] + r["step"])
            pv.append(p)
            row = {"step": r["step"], "rule": rule_text(r["pattern"], col2name),
                   "rule_columns": " AND ".join(f"{a}={v}" for a, v in r["pattern"]),
                   "n_conditions": len(r["pattern"]), "support": int(mk.sum()),
                   "support_share": float(mk.mean()), "target": tgt,
                   "mean_target": float(y[mk].mean()), "deviation": float(y[mk].mean() - y.mean())}
            for m in ("gpt", "claude", "mean", "diff"):
                col = f"{fam}_{m}"
                s = sub[col]
                row[f"deviation_{m}"] = float(s[mk].mean() - s.mean())
            for m in ("gpt", "claude"):
                for a in axes:
                    s = sub[f"axis_{a}_{m}"]
                    row[f"axisdev_{a}_{m}"] = float(s[mk].mean() - s.mean()) if s[mk].notna().any() else np.nan
            row["n_themes"] = int(sub.loc[mk, "theme"].nunique())
            row["gain"], row["perm_p"] = r["gain"], p
            rows.append(row)
        for row, a in zip(rows, bh(pv)):
            row["perm_p_bh"] = a
        out = run.path(f"et_{spec['name']}.csv")
        empty = pd.DataFrame(columns=["step", "rule", "rule_columns", "n_conditions", "support",
                                      "deviation", "deviation_gpt", "deviation_claude",
                                      "deviation_mean", "deviation_diff", "perm_p", "perm_p_bh"])
        (pd.DataFrame(rows) if rows else empty).to_csv(out, index=False)
        meta = {"name": spec["name"], "target": tgt, "n": int(len(sub)), "mean_target": float(y.mean()),
                "min_effect": eff, "max_conj": spec["max_conj"], "min_support": ec["min_support"],
                "rescale_range": [lo, hi], "n_candidate_patterns": res["n_candidates"],
                "n_eligible_patterns": res["n_eligible"], "split": "discovery", "columns": cols}
        write_json(run.path(f"et_{spec['name']}_partition_mean.json"), meta)
        write_meta(run, out, "6", **meta, note="permutation p ignores that rows were selected on "
                   "this split; optimistic by construction")
        log(f"6: et_{spec['name']}.csv {len(rows)} rows; {res['n_eligible']}/{res['n_candidates']} eligible")


def prereg(run: Run) -> None:
    pc = run.cfg["prereg"]
    out = run.path(pc["file"])
    if out.exists():
        die(f"{out.name} exists - preregistration is written once per run")
    tabs = {n: read_et(run.path(f"et_{n}.csv")) for n in ("gpt", "claude", "mean", "diff")}
    pool: dict[str, dict] = {}
    for n in ("gpt", "claude", "mean"):
        for r in tabs[n].itertuples():
            e = pool.setdefault(r.rule_columns, {"rule": r.rule, "rule_columns": r.rule_columns,
                                                 "tables": [], "support_discovery": int(r.support),
                                                 "deviation_gpt": r.deviation_gpt,
                                                 "deviation_claude": r.deviation_claude,
                                                 "deviation_mean": r.deviation_mean})
            e["tables"].append(n)
    elig = [e for e in pool.values() if np.sign(e["deviation_gpt"]) == np.sign(e["deviation_claude"])
            and e["deviation_gpt"] != 0]
    for e in pool.values():
        e["eligible"] = e in elig
    elig.sort(key=lambda e: (-len(e["tables"]), -min(abs(e["deviation_gpt"]), abs(e["deviation_claude"]))))
    rules = [{**e, "kind": "score"} for e in elig[:pc["max_rules"]]]
    if len(rules) < pc["max_rules"] and len(tabs["diff"]):
        dd = tabs["diff"].copy()
        dd["absdev"] = dd.deviation.abs()
        for r in dd.sort_values("absdev", ascending=False).itertuples():
            if len(rules) >= pc["max_rules"]:
                break
            rules.append({"rule": r.rule, "rule_columns": r.rule_columns, "tables": ["diff"],
                          "support_discovery": int(r.support), "deviation_diff": r.deviation,
                          "kind": "diff"})
    for i, r in enumerate(rules, 1):
        r["id"] = i
    shas = {f"et_{n}.csv": hashlib.sha256(run.path(f"et_{n}.csv").read_bytes()).hexdigest()
            for n in ("gpt", "claude", "mean", "diff")}
    obj = {"registered_at_utc": utcnow(), "target": run.cfg["target"],
           "target_family": run.cfg["target_family"], "rule": pc["rule"], "max_rules": pc["max_rules"],
           "confirmation_split_read": False, "source_tables_sha256": shas, "rules": rules,
           "pool_not_registered": [e for e in pool.values() if e["rule_columns"] not in
                                   {r["rule_columns"] for r in rules}]}
    write_json(out, obj)
    write_meta(run, out, "prereg", n_rules=len(rules))
    decide(run, "prereg", f"{len(rules)} rules registered ({sum(r['kind'] == 'score' for r in rules)} score, "
           f"{sum(r['kind'] == 'diff' for r in rules)} diff)", pc["rule"])
