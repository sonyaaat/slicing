"""Step 7 of the v5 corpus run - held-out confirmation. No model call.

Order of checks before the confirmation split is read:
  * preregistered_rules.json exists and every et_{gpt,claude,mean,diff}.csv still has the
    SHA-256 recorded in it (the tables were not changed after registration);
  * step 7 has not run before in this run directory (spec: confirmation is read once).

Criterion (spec, step 7; config confirm.*), per rule and target, on the confirmation split:
  same sign of the deviation as on discovery, support >= 40, and the 95% bootstrap interval
  (2,000 resamples of the rule's items) of the rule mean excludes the confirmation-split mean.
The deviation is in the table's own target (score_rel_gpt / _claude / _mean / _diff).
Preregistered rules are judged on the run target (score_rel_mean); the per-model results are
reported next to it. A permutation p on confirmation is stored for information only.

For confirmed rules, on all 4,027 messages: support, mean of the relative target and of the
clipped and unclipped raw scores per model, deviation in points (x100) and in percent of the
corpus mean of the clipped score, and the worst axis. Worst axis: per model, achieved points
on the axis / total positive points of the message (these shares sum to the unclipped score),
centred on the theme mean like the target; the row's term per axis is mean(row) - mean(all),
averaged over the two models; the worst axis is the one with the largest term in the
direction of the row's deviation. Its n = rule messages that have a criterion on that axis.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict

import numpy as np
import pandas as pd

from common import Run, die, log, read_json, write_json, write_meta
from et import permutation_p
from v5_data import load_data
from v5_infra import decide, utcnow
from v5_tables import column_target, read_et

MODELS = ("gpt", "claude", "mean")


def conds_of(rule_columns: str) -> list[tuple[str, str]]:
    return [tuple(x.split("=", 1)) for x in rule_columns.split(" AND ")]


def mask(df: pd.DataFrame, conds) -> np.ndarray:
    m = np.ones(len(df), dtype=bool)
    for c, v in conds:
        m &= (df[c].astype(str) == v).to_numpy()
    return m


def bootstrap_ci(y: np.ndarray, n: int, ci: float, seed) -> tuple[float, float]:
    if len(y) == 0:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    means = y[rng.integers(0, len(y), size=(n, len(y)))].mean(axis=1)
    lo = (1 - ci) / 2
    return float(np.quantile(means, lo)), float(np.quantile(means, 1 - lo))


def confirm(disc: pd.DataFrame, conf: pd.DataFrame, conds, target: str, cc: dict, seed) -> dict:
    d = disc[disc[target].notna()].reset_index(drop=True)
    c = conf[conf[target].notna()].reset_index(drop=True)
    md, mc = mask(d, conds), mask(c, conds)
    yd, yc = d[target].to_numpy(float), c[target].to_numpy(float)
    dev_d = float(yd[md].mean() - yd.mean()) if md.any() else np.nan
    dev_c = float(yc[mc].mean() - yc.mean()) if mc.any() else np.nan
    lo, hi = bootstrap_ci(yc[mc], cc["bootstrap_n"], cc["ci"], seed)
    same = bool(mc.any() and dev_d != 0 and np.sign(dev_c) == np.sign(dev_d))
    enough = int(mc.sum()) >= cc["min_support"]
    excl = bool(mc.any() and (hi < yc.mean() or lo > yc.mean()))
    p = permutation_p(yc, mc, 10000, int(np.random.default_rng(seed).integers(1 << 31))) \
        if 0 < mc.sum() < len(yc) else np.nan
    return {"target": target, "support_disc": int(md.sum()), "dev_disc": dev_d,
            "support_conf": int(mc.sum()), "mean_conf": float(yc[mc].mean()) if mc.any() else np.nan,
            "conf_split_mean": float(yc.mean()), "dev_conf": dev_c, "ci_low": lo, "ci_high": hi,
            "sign_same": same, "support_ok": enough, "ci_excludes_mean": excl,
            "confirmed": same and enough and excl,
            "shrinkage": dev_c / dev_d if dev_d and not np.isnan(dev_c) else np.nan,
            "perm_p_conf": p}


def axis_shares(run: Run, data: pd.DataFrame) -> dict[str, pd.DataFrame]:
    cr = pd.read_csv(run.path("corpus_criteria.csv"))
    pos = cr.points.where(cr.points > 0, 0).groupby(cr.prompt_id).sum()
    th = data.set_index("prompt_id").theme
    out = {}
    for m in ("gpt", "claude"):
        ach = cr.points.where(cr[f"met_{m}"] == True, 0)  # noqa: E712
        t = ach.groupby([cr.prompt_id, cr.axis]).sum().unstack("axis").fillna(0.0)
        s = t.div(pos, axis=0).reindex(data.prompt_id).fillna(0.0)
        s = s - s.groupby(th.reindex(s.index).to_numpy()).transform("mean")
        out[m] = s.reset_index(drop=True)
    return out


def worst_axis(shares, data, mk) -> tuple[str, float, int, dict]:
    terms = sum(shares[m][mk].mean() - shares[m].mean() for m in ("gpt", "claude")) / 2
    a = terms.idxmin() if terms.sum() < 0 else terms.idxmax()
    n = int(data.loc[mk, f"axis_{a}_gpt"].notna().sum())
    return a, float(terms[a]), n, {k: round(float(v), 4) for k, v in terms.items()}


def run(run: Run) -> None:
    cfg = run.cfg
    cc = dict(cfg["confirm"])
    seed = cfg["split"]["seed"]
    pre_path = run.path(cfg["prereg"]["file"])
    if not pre_path.exists():
        die("preregistered_rules.json missing - step 7 must not run without it")
    pre = read_json(pre_path)
    for f, sha in pre["source_tables_sha256"].items():
        now = hashlib.sha256(run.path(f).read_bytes()).hexdigest()
        if now != sha:
            die(f"{f} changed after preregistration ({sha[:12]} -> {now[:12]})")
    if run.path("step7_summary.json").exists():
        die("step 7 already ran in this run directory; the confirmation split is read once")
    t_read = utcnow()
    decide(run, "7", "confirmation split read for the first time",
           f"preregistration at {pre['registered_at_utc']}; table hashes verified")

    df = load_data(run)
    sp = pd.read_csv(run.path("split_corpus.csv"))
    ann = pd.read_csv(run.path("annotations_full.csv"), keep_default_na=False)
    data = df.merge(sp[["prompt_id", "split"]], on="prompt_id").merge(
        ann.drop(columns="theme"), on="prompt_id").sort_values("prompt_id").reset_index(drop=True)
    if len(data) != len(df):
        die("annotations_full.csv does not cover every message")
    data["score_mean_raw"] = (data.score_gpt_raw + data.score_claude_raw) / 2
    disc = data[data.split == "discovery"].reset_index(drop=True)
    conf = data[data.split == "confirmation"].reset_index(drop=True)
    run_target = cfg["target"]

    # ------------------------------------------------------------ preregistered
    pre_rows = []
    for r in pre["rules"]:
        conds = conds_of(r["rule_columns"])
        tgts = [run_target] + [column_target(run, m) for m in ("gpt", "claude")] \
            if r["kind"] == "score" else [column_target(run, "diff")]
        res = {t: confirm(disc, conf, conds, t, cc, [seed, 700, r["id"], i]) for i, t in enumerate(tgts)}
        main = res[tgts[0]]
        row = {"id": r["id"], "kind": r["kind"], "rule": r["rule"], "rule_columns": r["rule_columns"],
               "tables": ",".join(r["tables"]), **main}
        if r["kind"] == "score":
            for m in ("gpt", "claude"):
                x = res[column_target(run, m)]
                row.update({f"{m}_dev_conf": x["dev_conf"], f"{m}_ci": f"[{x['ci_low']:+.4f}, {x['ci_high']:+.4f}]",
                            f"{m}_confirmed": x["confirmed"]})
        pre_rows.append(row)
    pre_df = pd.DataFrame(pre_rows)
    pre_df.to_csv(run.path("preregistered_confirm.csv"), index=False)

    # ------------------------------------------------------------ every table row
    per_table, confirmed = {}, defaultdict(list)
    for ti, t in enumerate(cfg["et"]["tables"]):
        et = read_et(run.path(f"et_{t['name']}.csv"))
        tgt = column_target(run, t["model"])
        rows = []
        for r in et.to_dict("records"):
            conds = conds_of(r["rule_columns"])
            res = confirm(disc, conf, conds, tgt, cc, [seed, ti, int(r["step"])])
            if res["support_disc"] != int(r["support"]) or abs(res["dev_disc"] - r["deviation"]) > 1e-9:
                die(f"et_{t['name']} row {r['step']}: discovery numbers do not reproduce")
            rows.append({"table": t["name"], "step": int(r["step"]), "rule": r["rule"],
                         "rule_columns": r["rule_columns"], **res})
            if res["confirmed"]:
                key = " AND ".join(sorted(r["rule_columns"].split(" AND ")))
                confirmed[key].append({"table": t["name"], "step": int(r["step"]), "rule": r["rule"],
                                       "rule_columns": r["rule_columns"]})
        tab = pd.DataFrame(rows)
        tab.to_csv(run.path(f"et_{t['name']}_confirm.csv"), index=False)
        per_table[t["name"]] = {"k": int(tab.confirmed.sum()) if len(tab) else 0, "m": len(tab)}
    for r in pre_rows:
        if r["confirmed"]:
            key = " AND ".join(sorted(r["rule_columns"].split(" AND ")))
            confirmed[key].append({"table": f"prereg#{r['id']}", "step": r["id"], "rule": r["rule"],
                                   "rule_columns": r["rule_columns"]})

    # ------------------------------------------------------------ full-corpus table
    shares = axis_shares(run, data)
    reg_keys = {" AND ".join(sorted(r["rule_columns"].split(" AND "))): r["id"] for r in pre["rules"]}
    mean_clip = {m: float(data[f"score_{m}"].mean()) for m in MODELS}
    mean_raw = {m: float(data[f"score_{m}_raw"].mean()) for m in MODELS}
    final = []
    for key, hits in confirmed.items():
        conds = conds_of(hits[0]["rule_columns"])
        mk = mask(data, conds)
        row = {"rule": hits[0]["rule"], "rule_columns": hits[0]["rule_columns"],
               "preregistered_id": reg_keys.get(key), "confirmed_in": ", ".join(
                   f"{h['table']}" + ("" if h["table"].startswith("prereg") else f"#{h['step']}") for h in hits),
               "n_disc": int((mk & (data.split == "discovery")).sum()),
               "n_conf": int((mk & (data.split == "confirmation")).sum()), "n_full": int(mk.sum()),
               "themes": int(data.loc[mk, "theme"].nunique())}
        for m in MODELS:
            rel = float(data[f"score_rel_{m}"][mk].mean() - data[f"score_rel_{m}"].mean())
            row[f"{m}_rel_dev_pts"] = 100 * rel
            row[f"{m}_rel_dev_pct"] = 100 * rel / mean_clip[m]
            v = float(data[f"score_{m}"][mk].mean())
            row[f"{m}_mean_clipped"] = v
            row[f"{m}_clipped_dev_pts"] = 100 * (v - mean_clip[m])
            row[f"{m}_clipped_dev_pct"] = 100 * (v - mean_clip[m]) / mean_clip[m]
            w = float(data[f"score_{m}_raw"][mk].mean())
            row[f"{m}_raw_dev_pts"] = 100 * (w - mean_raw[m])
            row[f"{m}_raw_dev_pct"] = 100 * (w - mean_raw[m]) / mean_raw[m]
        a, term, n_a, terms = worst_axis(shares, data, mk)
        row.update(worst_axis=a, worst_axis_term_pts=100 * term, worst_axis_n=n_a,
                   axis_terms=json.dumps(terms))
        final.append(row)
    ft = pd.DataFrame(final)
    if len(ft):
        ft = ft.sort_values("mean_rel_dev_pts").reset_index(drop=True)
    ft.to_csv(run.path("FINAL_TABLE_CORPUS.csv"), index=False)

    summ = {"confirmation_read_at_utc": t_read, "preregistered_at_utc": pre["registered_at_utc"],
            "n_full": len(data), "n_discovery": len(disc), "n_confirmation": len(conf),
            "confirm_params": cc, "run_target": run_target,
            "preregistered_confirmed": int(pre_df.confirmed.sum()), "preregistered_total": len(pre_df),
            "per_table": per_table, "n_final_rules": len(ft),
            "corpus_means_clipped": mean_clip, "corpus_means_raw": mean_raw,
            "worst_axis_definition": "per model, achieved points on the axis / total positive points "
                                     "(sums to the unclipped score), centred on the theme mean; row "
                                     "term = mean(row) - mean(all), averaged over gpt and claude; the "
                                     "axis with the largest term in the direction of the deviation; "
                                     "n = rule messages with a criterion on that axis"}
    write_json(run.path("step7_summary.json"), summ)
    for f in ("preregistered_confirm.csv", "FINAL_TABLE_CORPUS.csv"):
        write_meta(run, run.path(f), "7", api_calls=0, confirmation_read_at_utc=t_read)
    log(f"7: preregistered {summ['preregistered_confirmed']}/{len(pre_df)}; "
        + "; ".join(f"{k} {v['k']}/{v['m']}" for k, v in per_table.items())
        + f"; final table {len(ft)} rules")
    import v5_report7
    v5_report7.write(run, pre_df, per_table, ft, summ)
