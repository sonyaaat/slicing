"""Subset run S2 on an existing v5 corpus run. No model call.

Subset S2: messages where at least 2 of {episode_timing, symptom_course, possible_trigger}
hold a value outside {not_applicable, unknown, parse_error}. Attributes: the seven content
attributes plus theme; the three form attributes are excluded. Values unknown /
not_applicable / parse_error / other / "none of these" never enter a rule; not_stated does.

Scopes
  corpus              target score_rel_mean (theme-centred); tables gpt / claude / mean on
                      score_rel_<m>; support >= 60, |effect| >= 0.05
  theme:<t>           drill-down inside a theme on the absolute score_<m>; theme is not an
                      attribute there; support >= 20, |effect| >= 0.08
Tables are built on the S2 part of the existing discovery split (max 2 conditions, up to 8
rows), preregistered (UTC timestamp, SHA-256 of the tables; same-sign-across-models
eligibility and the ranking of the main run), then confirmed on the S2 part of the existing
confirmation split: same sign, support >= 40 (corpus) / >= 12 (theme), 95% bootstrap CI of
the rule mean excludes the confirmation-part mean. Confirmed rules are recomputed on all S2
items of their scope (deviation in points and percent, worst axis with n).

The confirmation items were already read once by step 7 of the main run; this is their
second read, and the report says so.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Run, die, log, read_json, write_json, write_meta  # noqa: E402
from et import bh, permutation_p  # noqa: E402
from v5_infra import decide, utcnow  # noqa: E402
from v5_step7 import axis_shares, bootstrap_ci, conds_of, mask, worst_axis  # noqa: E402
from v5_tables import mask_of, read_et, rule_text, search  # noqa: E402

TRIPLE = ["episode_timing", "symptom_course", "possible_trigger"]
NONAPPL = {"not_applicable", "unknown", "parse_error"}
ATTRS = ["patient_age", "episode_timing", "possible_trigger", "care_setting", "symptom_course",
         "intervention_type", "evidence_basis"]
FORM_EXCLUDED = ["request_structure", "output_constraints", "source_material"]
EXCLUDE_VALUES = ["unknown", "not_applicable", "parse_error", "other", "none of these"]
MODELS = ("gpt", "claude", "mean")
DRILL_THEMES = ["emergency_referrals", "communication"]

PARAMS = {
    "subset": {"name": "S2", "rule": "at least 2 of {episode_timing, symptom_course, possible_trigger} "
               "hold a value not in {not_applicable, unknown, parse_error}"},
    "attributes": ATTRS + ["theme"], "excluded_form_attributes": FORM_EXCLUDED,
    "exclude_values": EXCLUDE_VALUES,
    "corpus": {"target": "score_rel_mean", "family": "score_rel", "min_support": 60, "min_effect": 0.05,
               "max_conj": 2, "max_rows": 8, "prereg_max_rules": 10, "confirm_min_support": 40},
    "theme": {"target": "score_mean", "family": "score", "min_support": 20, "min_effect": 0.08,
              "max_conj": 2, "max_rows": 8, "prereg_max_rules": 6, "confirm_min_support": 12,
              "themes": DRILL_THEMES, "theme_choice": "two highest step-0 R2 (score_rel_mean, r2_cv_mean): "
              "emergency_referrals 0.210, communication 0.150"},
    "bootstrap_n": 2000, "ci": 0.95, "permutation_n": 10000, "permutation_seed": 42, "seed": 42,
    "prereg_rule": "Pool: distinct rules of the 2-condition tables gpt/claude/mean of the scope. Eligible: "
                   "deviation on discovery has the same sign for gpt and claude. Rank: number of the three "
                   "tables containing the rule (desc), then min(|dev gpt|, |dev claude|) (desc). Take up to "
                   "max_rules. No diff fill.",
}


def md(df: pd.DataFrame, nd: int = 4) -> str:
    if not len(df):
        return "_(no rows)_\n"
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                cells.append("" if np.isnan(v) else f"{v:.{nd}f}")
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def build_table(data: pd.DataFrame, cols: list[str], tgt: str, fam: str, p: dict, col2name: dict,
                axes: list[str]) -> tuple[pd.DataFrame, dict]:
    res, ok, lo, hi = search(data, cols, tgt, max_conj=p["max_conj"], min_support=p["min_support"],
                             min_effect=p["min_effect"], max_rows=p["max_rows"], exclude=EXCLUDE_VALUES)
    sub = data[ok].reset_index(drop=True)
    y = sub[tgt].to_numpy(float)
    rows, pv = [], []
    for r in res["rows"]:
        mk = mask_of(sub, r["pattern"])
        pp = permutation_p(y, mk, PARAMS["permutation_n"], PARAMS["permutation_seed"] + r["step"])
        pv.append(pp)
        row = {"step": r["step"], "rule": rule_text(r["pattern"], col2name),
               "rule_columns": " AND ".join(f"{a}={v}" for a, v in r["pattern"]),
               "n_conditions": len(r["pattern"]), "support": int(mk.sum()),
               "support_share": float(mk.mean()), "target": tgt,
               "mean_target": float(y[mk].mean()), "deviation": float(y[mk].mean() - y.mean())}
        for m in MODELS:
            s = sub[f"{fam}_{m}"]
            row[f"deviation_{m}"] = float(s[mk].mean() - s.mean())
        for m in ("gpt", "claude"):
            for a in axes:
                s = sub[f"axis_{a}_{m}"]
                row[f"axisdev_{a}_{m}"] = float(s[mk].mean() - s.mean()) if s[mk].notna().any() else np.nan
        row["n_themes"] = int(sub.loc[mk, "theme"].nunique())
        row["gain"], row["perm_p"] = r["gain"], pp
        rows.append(row)
    for row, a in zip(rows, bh(pv)):
        row["perm_p_bh"] = a
    empty = pd.DataFrame(columns=["step", "rule", "rule_columns", "n_conditions", "support", "deviation",
                                  "deviation_gpt", "deviation_claude", "deviation_mean", "perm_p", "perm_p_bh"])
    meta = {"target": tgt, "n": int(len(sub)), "mean_target": float(y.mean()), "rescale_range": [lo, hi],
            "n_candidate_patterns": res["n_candidates"], "n_eligible_patterns": res["n_eligible"],
            "split": "discovery (S2 part)", "columns": cols, **{k: p[k] for k in
            ("min_support", "min_effect", "max_conj", "max_rows")}}
    return (pd.DataFrame(rows) if rows else empty), meta


def prereg_scope(tabs: dict[str, pd.DataFrame], max_rules: int) -> tuple[list[dict], list[dict]]:
    pool: dict[str, dict] = {}
    for n in ("gpt", "claude", "mean"):
        for r in tabs[n].itertuples():
            e = pool.setdefault(r.rule_columns, {"rule": r.rule, "rule_columns": r.rule_columns, "tables": [],
                                                 "support_discovery": int(r.support),
                                                 "deviation_gpt": float(r.deviation_gpt),
                                                 "deviation_claude": float(r.deviation_claude),
                                                 "deviation_mean": float(r.deviation_mean)})
            e["tables"].append(n)
    elig = [e for e in pool.values() if e["deviation_gpt"] != 0
            and np.sign(e["deviation_gpt"]) == np.sign(e["deviation_claude"])]
    for e in pool.values():
        e["eligible"] = e in elig
    elig.sort(key=lambda e: (-len(e["tables"]), -min(abs(e["deviation_gpt"]), abs(e["deviation_claude"]))))
    rules = [{**e, "kind": "score"} for e in elig[:max_rules]]
    rest = [e for e in pool.values() if e["rule_columns"] not in {r["rule_columns"] for r in rules}]
    return rules, rest


def confirm(disc: pd.DataFrame, conf: pd.DataFrame, conds, target: str, min_support: int, seed) -> dict:
    d = disc[disc[target].notna()].reset_index(drop=True)
    c = conf[conf[target].notna()].reset_index(drop=True)
    mdk, mc = mask(d, conds), mask(c, conds)
    yd, yc = d[target].to_numpy(float), c[target].to_numpy(float)
    dev_d = float(yd[mdk].mean() - yd.mean()) if mdk.any() else np.nan
    dev_c = float(yc[mc].mean() - yc.mean()) if mc.any() else np.nan
    lo, hi = bootstrap_ci(yc[mc], PARAMS["bootstrap_n"], PARAMS["ci"], seed)
    same = bool(mc.any() and dev_d != 0 and np.sign(dev_c) == np.sign(dev_d))
    enough = int(mc.sum()) >= min_support
    excl = bool(mc.any() and (hi < yc.mean() or lo > yc.mean()))
    pp = permutation_p(yc, mc, 10000, int(np.random.default_rng(seed).integers(1 << 31))) \
        if 0 < mc.sum() < len(yc) else np.nan
    return {"target": target, "support_disc": int(mdk.sum()), "dev_disc": dev_d,
            "support_conf": int(mc.sum()), "mean_conf": float(yc[mc].mean()) if mc.any() else np.nan,
            "conf_part_mean": float(yc.mean()), "dev_conf": dev_c, "ci_low": lo, "ci_high": hi,
            "sign_same": same, "support_ok": enough, "ci_excludes_mean": excl,
            "confirmed": bool(same and enough and excl),
            "shrinkage": dev_c / dev_d if dev_d and not np.isnan(dev_c) else np.nan,
            "perm_p_conf": pp}


def run(run_dir: Path) -> None:
    run = Run(run_dir)
    out = run.path("subset_s2")
    out.mkdir(exist_ok=True)
    opath = lambda n: out / n  # noqa: E731
    if opath("step7_summary_subset.json").exists():
        die("subset run already confirmed in this directory; remove subset_s2/ to redo")
    t0 = utcnow()
    axes = run.cfg["data"]["axes"]

    # ---------------------------------------------------------------- data and subset
    df = pd.read_csv(run.path("corpus_data.csv"))
    sp = pd.read_csv(run.path("split_corpus.csv"))
    ann = pd.read_csv(run.path("annotations_full.csv"), keep_default_na=False)
    full = df.merge(sp[["prompt_id", "split"]], on="prompt_id").merge(
        ann.drop(columns="theme"), on="prompt_id").sort_values("prompt_id").reset_index(drop=True)
    if len(full) != len(df) or len(full) != 4027:
        die("join does not cover every message")
    full["score_mean_raw"] = (full.score_gpt_raw + full.score_claude_raw) / 2
    n_app = sum((~full[c].isin(NONAPPL)).astype(int) for c in TRIPLE)
    full["in_s2"] = n_app >= 2
    s2 = full[full.in_s2].reset_index(drop=True)
    n_s2 = int(len(s2))
    disc = s2[s2.split == "discovery"].reset_index(drop=True)
    conf = s2[s2.split == "confirmation"].reset_index(drop=True)
    log(f"S2: {n_s2} items; discovery {len(disc)}, confirmation {len(conf)}")

    # record the rule and size in the run's config (the only edit made to it)
    cfg_path = run.path("run_config.json")
    cfg = json.loads(cfg_path.read_text())
    cfg["subset_s2"] = {"rule": PARAMS["subset"]["rule"], "n": n_s2, "n_discovery": int(len(disc)),
                        "n_confirmation": int(len(conf)), "recorded_at_utc": t0,
                        "attributes": PARAMS["attributes"], "excluded_form_attributes": FORM_EXCLUDED,
                        "exclude_values": EXCLUDE_VALUES, "corpus": PARAMS["corpus"], "theme": PARAMS["theme"],
                        "output_dir": "subset_s2/"}
    cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    run.cfg = cfg
    decide(run, "subset", f"subset S2 defined: {n_s2} of 4027 items ({len(disc)} discovery / {len(conf)} confirmation)",
           PARAMS["subset"]["rule"] + "; rule and sizes recorded in run_config.json key subset_s2")

    # ---------------------------------------------------------------- what the subset excludes
    shift = {}
    th = pd.crosstab(full.theme, full.in_s2).rename(columns={True: "in_S2", False: "out_S2"})
    th["total"] = th.sum(axis=1); th["share_in"] = th.in_S2 / th.total
    shift["theme"] = th.reset_index()
    pc = pd.crosstab(full.physician_category, full.in_s2).rename(columns={True: "in_S2", False: "out_S2"})
    pc["total"] = pc.sum(axis=1); pc["share_in"] = pc.in_S2 / pc.total
    shift["physician_category"] = pc.sort_values("share_in").reset_index()
    for k, v in shift.items():
        v.to_csv(opath(f"subset_shift_{k}.csv"), index=False)

    # ---------------------------------------------------------------- scopes
    fin = read_json(run.path("attributes_final.json"))["attributes"]
    col2name = {a["column"]: a["name"] for a in fin} | {"theme": "theme"}
    scopes = [{"key": "corpus", "label": "corpus", "data_disc": disc, "data_conf": conf, "data_all": s2,
               "cols": ATTRS + ["theme"], **PARAMS["corpus"]}]
    for t in DRILL_THEMES:
        scopes.append({"key": f"theme_{t}", "label": f"theme:{t}", "data_disc": disc[disc.theme == t].reset_index(drop=True),
                       "data_conf": conf[conf.theme == t].reset_index(drop=True),
                       "data_all": s2[s2.theme == t].reset_index(drop=True), "cols": ATTRS, **PARAMS["theme"]})

    # ---------------------------------------------------------------- tables (discovery only)
    table_meta = {}
    for sc in scopes:
        for m in MODELS:
            tgt = f"{sc['family']}_{m}"
            tab, meta = build_table(sc["data_disc"], sc["cols"], tgt, sc["family"], sc, col2name, axes)
            f = opath(f"et_{sc['key']}_{m}.csv")
            tab.to_csv(f, index=False)
            write_meta(run, f, "subset-6", **meta, scope=sc["label"], note="permutation p ignores that rows "
                       "were selected on this split; optimistic by construction")
            table_meta[f"{sc['key']}_{m}"] = meta
            log(f"et_{sc['key']}_{m}: {len(tab)} rows; {meta['n_eligible_patterns']}/{meta['n_candidate_patterns']} eligible; n={meta['n']}")

    # ---------------------------------------------------------------- preregistration
    pre_all = {"registered_at_utc": utcnow(), "rule": PARAMS["prereg_rule"], "confirmation_part_read": False,
               "note": "the confirmation items were read once before by step 7 of the main run; this subset "
                       "run is their second read", "scopes": {}}
    for sc in scopes:
        tabs = {m: read_et(opath(f"et_{sc['key']}_{m}.csv")) for m in MODELS}
        rules, rest = prereg_scope(tabs, sc["prereg_max_rules"])
        for i, r in enumerate(rules, 1):
            r["id"] = i
        shas = {f"et_{sc['key']}_{m}.csv": hashlib.sha256(opath(f"et_{sc['key']}_{m}.csv").read_bytes()).hexdigest()
                for m in MODELS}
        pre_all["scopes"][sc["key"]] = {"label": sc["label"], "target": sc["target"], "max_rules": sc["prereg_max_rules"],
                                        "source_tables_sha256": shas, "rules": rules, "pool_not_registered": rest}
        log(f"prereg {sc['key']}: {len(rules)} rules (pool {len(rules) + len(rest)})")
    write_json(opath("preregistered_rules_subset.json"), pre_all)
    write_meta(run, opath("preregistered_rules_subset.json"), "subset-prereg",
               n_rules={k: len(v["rules"]) for k, v in pre_all["scopes"].items()})
    decide(run, "subset-prereg", "rules registered: " + ", ".join(f"{k} {len(v['rules'])}" for k, v in pre_all["scopes"].items()),
           PARAMS["prereg_rule"])

    # ---------------------------------------------------------------- confirmation (second read)
    for sc in scopes:
        for f, sha in pre_all["scopes"][sc["key"]]["source_tables_sha256"].items():
            if hashlib.sha256(opath(f).read_bytes()).hexdigest() != sha:
                die(f"{f} changed after preregistration")
    t_read = utcnow()
    decide(run, "subset-7", "confirmation part of S2 read (second read of these items)",
           f"first read by step 7 of the main run at {read_json(run.path('step7_summary.json'))['confirmation_read_at_utc']}; "
           f"subset preregistration at {pre_all['registered_at_utc']}; table hashes verified")
    seed = PARAMS["seed"]
    shares_full = axis_shares(run, full)              # centred on theme means over all 4,027
    shares_s2 = {m: v[full.in_s2.to_numpy()].reset_index(drop=True) for m, v in shares_full.items()}

    pre_frames, per_table, finals, summ_scopes = {}, {}, {}, {}
    for si, sc in enumerate(scopes):
        d, c, allp = sc["data_disc"], sc["data_conf"], sc["data_all"]
        rows = []
        for r in pre_all["scopes"][sc["key"]]["rules"]:
            conds = conds_of(r["rule_columns"])
            tg = [sc["target"]] + [f"{sc['family']}_{m}" for m in ("gpt", "claude")]
            res = {t: confirm(d, c, conds, t, sc["confirm_min_support"], [seed, 700 + si, r["id"], i]) for i, t in enumerate(tg)}
            row = {"scope": sc["label"], "id": r["id"], "rule": r["rule"], "rule_columns": r["rule_columns"],
                   "tables": ",".join(r["tables"]), **res[tg[0]]}
            for m in ("gpt", "claude"):
                x = res[f"{sc['family']}_{m}"]
                row.update({f"{m}_dev_conf": x["dev_conf"], f"{m}_ci": f"[{x['ci_low']:+.4f}, {x['ci_high']:+.4f}]",
                            f"{m}_confirmed": x["confirmed"]})
            rows.append(row)
        pre_df = pd.DataFrame(rows)
        pre_df.to_csv(opath(f"preregistered_confirm_{sc['key']}.csv"), index=False)
        pre_frames[sc["key"]] = pre_df

        confirmed = defaultdict(list)
        for m in MODELS:
            et = read_et(opath(f"et_{sc['key']}_{m}.csv"))
            tgt = f"{sc['family']}_{m}"
            trows = []
            for r in et.to_dict("records"):
                conds = conds_of(r["rule_columns"])
                res = confirm(d, c, conds, tgt, sc["confirm_min_support"], [seed, si, MODELS.index(m), int(r["step"])])
                if res["support_disc"] != int(r["support"]) or abs(res["dev_disc"] - r["deviation"]) > 1e-9:
                    die(f"et_{sc['key']}_{m} row {r['step']}: discovery numbers do not reproduce")
                trows.append({"table": m, "step": int(r["step"]), "rule": r["rule"], "rule_columns": r["rule_columns"], **res})
                if res["confirmed"]:
                    key = " AND ".join(sorted(r["rule_columns"].split(" AND ")))
                    confirmed[key].append({"table": m, "step": int(r["step"]), "rule": r["rule"], "rule_columns": r["rule_columns"]})
            tab = pd.DataFrame(trows)
            tab.to_csv(opath(f"et_{sc['key']}_{m}_confirm.csv"), index=False)
            per_table[f"{sc['key']}_{m}"] = {"k": int(tab.confirmed.sum()) if len(tab) else 0, "m": int(len(tab))}
        for r in rows:
            if r["confirmed"]:
                key = " AND ".join(sorted(r["rule_columns"].split(" AND ")))
                confirmed[key].append({"table": f"prereg#{r['id']}", "step": r["id"], "rule": r["rule"], "rule_columns": r["rule_columns"]})

        # recompute confirmed rules on all S2 items of the scope
        reg_keys = {" AND ".join(sorted(r["rule_columns"].split(" AND "))): r["id"] for r in pre_all["scopes"][sc["key"]]["rules"]}
        in_scope = s2.index.isin(allp.index) if sc["key"] == "corpus" else (s2.theme == sc["label"].split(":")[1]).to_numpy()
        sh = {m: v[in_scope].reset_index(drop=True) for m, v in shares_s2.items()}
        mean_clip = {m: float(allp[f"score_{m}"].mean()) for m in MODELS}
        mean_raw = {m: float(allp[f"score_{m}_raw"].mean()) for m in MODELS}
        fin_rows = []
        for key, hits in confirmed.items():
            conds = conds_of(hits[0]["rule_columns"])
            mk = mask(allp, conds)
            row = {"scope": sc["label"], "rule": hits[0]["rule"], "rule_columns": hits[0]["rule_columns"],
                   "preregistered_id": reg_keys.get(key),
                   "confirmed_in": ", ".join(h["table"] + ("" if h["table"].startswith("prereg") else f"#{h['step']}") for h in hits),
                   "n_disc": int((mk & (allp.split == "discovery")).sum()), "n_conf": int((mk & (allp.split == "confirmation")).sum()),
                   "n_all_s2": int(mk.sum()), "themes": int(allp.loc[mk, "theme"].nunique())}
            for m in MODELS:
                tcol = f"{sc['family']}_{m}"
                dev = float(allp[tcol][mk].mean() - allp[tcol].mean())
                row[f"{m}_target_dev_pts"] = 100 * dev
                row[f"{m}_target_dev_pct"] = 100 * dev / mean_clip[m]
                v = float(allp[f"score_{m}"][mk].mean())
                row[f"{m}_mean_clipped"] = v
                row[f"{m}_clipped_dev_pts"] = 100 * (v - mean_clip[m])
                row[f"{m}_clipped_dev_pct"] = 100 * (v - mean_clip[m]) / mean_clip[m]
                w = float(allp[f"score_{m}_raw"][mk].mean())
                row[f"{m}_raw_dev_pts"] = 100 * (w - mean_raw[m])
                row[f"{m}_raw_dev_pct"] = 100 * (w - mean_raw[m]) / mean_raw[m]
            a, term, n_a, terms = worst_axis(sh, allp, mk)
            row.update(worst_axis=a, worst_axis_term_pts=100 * term, worst_axis_n=n_a, axis_terms=json.dumps(terms))
            fin_rows.append(row)
        ft = pd.DataFrame(fin_rows)
        if len(ft):
            ft = ft.sort_values("mean_target_dev_pts").reset_index(drop=True)
        ft.to_csv(opath(f"FINAL_TABLE_{sc['key']}.csv"), index=False)
        finals[sc["key"]] = ft
        summ_scopes[sc["key"]] = {"label": sc["label"], "target": sc["target"], "n_all_s2": int(len(allp)),
                                  "n_discovery": int(len(d)), "n_confirmation": int(len(c)),
                                  "min_support": sc["min_support"], "min_effect": sc["min_effect"],
                                  "confirm_min_support": sc["confirm_min_support"],
                                  "preregistered_confirmed": int(pre_df.confirmed.sum()) if len(pre_df) else 0,
                                  "preregistered_total": int(len(pre_df)),
                                  "per_table": {m: per_table[f"{sc['key']}_{m}"] for m in MODELS},
                                  "n_final_rules": int(len(ft)), "means_clipped": mean_clip, "means_raw": mean_raw}
        log(f"{sc['key']}: prereg {summ_scopes[sc['key']]['preregistered_confirmed']}/{len(pre_df)}; "
            + "; ".join(f"{m} {per_table[f'{sc['key']}_{m}']['k']}/{per_table[f'{sc['key']}_{m}']['m']}" for m in MODELS)
            + f"; final {len(ft)}")

    summ = {"started_at_utc": t0, "preregistered_at_utc": pre_all["registered_at_utc"], "confirmation_read_at_utc": t_read,
            "second_read_of_confirmation_items": True,
            "first_read_at_utc": read_json(run.path("step7_summary.json"))["confirmation_read_at_utc"],
            "subset": PARAMS["subset"], "n_s2": n_s2, "n_discovery": int(len(disc)), "n_confirmation": int(len(conf)),
            "scopes": summ_scopes, "params": {k: v for k, v in PARAMS.items() if k not in ("subset",)},
            "other_models": {"decision": "not added", "reason": "MedGemma (vllm/google/medgemma-27b-text-it, log "
                             "2026-07-24T12-08-49) and PLaMo (openai-api/plamo/plamo-3.0-prime, log 2026-07-16T05-23-21) "
                             "were judged by openai/gpt-4.1 with a length-adjustment penalty (center 2000 chars, "
                             "0.0299 per 500 chars); GPT-5.5 and Claude Opus 4.7 were judged by openai/gpt-4o-mini "
                             "without it. Same prompt_ids (4,027/4,027 verified earlier for PLaMo), different grader: "
                             "scores are not comparable in one table (project rule: never mix judge models)."},
            "worst_axis_definition": read_json(run.path("step7_summary.json"))["worst_axis_definition"]}
    write_json(opath("step7_summary_subset.json"), summ)
    for sc in scopes:
        for f in (f"preregistered_confirm_{sc['key']}.csv", f"FINAL_TABLE_{sc['key']}.csv"):
            write_meta(run, opath(f), "subset-7", api_calls=0, confirmation_read_at_utc=t_read, second_read=True)
    write_report(run, out, summ, shift, pre_frames, per_table, finals, scopes, table_meta)


def write_report(run, out, summ, shift, pre_frames, per_table, finals, scopes, table_meta):
    L = ["# Sliceability v5 — corpus run 1, subset run S2\n",
         f"Run `{run.dir.name}`, outputs in `subset_s2/`. No model call. Started {summ['started_at_utc']} (UTC); "
         f"rules registered at {summ['preregistered_at_utc']}; confirmation part read at {summ['confirmation_read_at_utc']}.\n",
         "**This is the second read of these confirmation items.** Step 7 of the main run read the full confirmation "
         f"split at {summ['first_read_at_utc']}. The subset rule, the attribute set and all thresholds below were fixed "
         "before this run started, but the items themselves are no longer unseen, and the confirmation here is weaker "
         "than a first read.\n",
         "## 1. Subset definition and what it excludes\n",
         f"**S2** = {summ['subset']['rule']}. n = {summ['n_s2']} of 4,027 ({100*summ['n_s2']/4027:.1f}%); "
         f"existing split restricted to S2: discovery {summ['n_discovery']}, confirmation {summ['n_confirmation']}.\n",
         "Attributes: " + ", ".join(PARAMS["attributes"]) + ". Excluded form attributes: " + ", ".join(FORM_EXCLUDED)
         + ". Values never in a rule: " + ", ".join(EXCLUDE_VALUES) + "; `not_stated` is allowed.\n",
         "**Theme shift** (items in / out of S2 per theme):\n", md(shift["theme"], 3),
         "\n**Physician-category shift** (sorted by share retained):\n", md(shift["physician_category"], 3),
         "\n**Other models.** " + summ["other_models"]["reason"] + " The run continues with two models.\n"]
    L.append("## 2. Tables on the S2 discovery part\n")
    for sc in scopes:
        L.append(f"### Scope {sc['label']} — target `{sc['target']}`, support ≥ {sc['min_support']}, |effect| ≥ {sc['min_effect']}, "
                 f"max 2 conditions, up to 8 rows\n")
        for m in MODELS:
            meta = table_meta[f"{sc['key']}_{m}"]
            et = read_et(out / f"et_{sc['key']}_{m}.csv")
            L.append(f"**et_{sc['key']}_{m}** (target `{meta['target']}`, n = {meta['n']}, discovery-part mean "
                     f"{meta['mean_target']:.4f}, {meta['n_eligible_patterns']}/{meta['n_candidate_patterns']} eligible patterns)\n")
            cols = [c for c in ["step", "rule", "support", "support_share", "mean_target", "deviation", "deviation_gpt",
                                "deviation_claude", "deviation_mean", "n_themes", "perm_p", "perm_p_bh"] if c in et.columns]
            L.append(md(et[cols], 4) if len(et) else "_(no row passed support and effect)_\n")
    L.append("## 3. Preregistered rules and confirmation\n")
    L.append(f"Preregistration rule: {PARAMS['prereg_rule']}\n")
    L.append("Confirmation on the S2 part of the confirmation split: same sign as on discovery, support ≥ "
             f"{PARAMS['corpus']['confirm_min_support']} (corpus) / ≥ {PARAMS['theme']['confirm_min_support']} (theme), "
             f"{int(PARAMS['ci']*100)}% bootstrap CI ({PARAMS['bootstrap_n']} resamples) of the rule mean excludes the "
             "confirmation-part mean. Judged on the scope target; gpt / claude columns apply the same criterion per model.\n")
    for sc in scopes:
        s = summ["scopes"][sc["key"]]
        pre = pre_frames[sc["key"]]
        L.append(f"### {sc['label']} — {s['preregistered_confirmed']} of {s['preregistered_total']} preregistered rules confirmed\n")
        if len(pre):
            cols = ["id", "rule", "tables", "support_disc", "dev_disc", "support_conf", "dev_conf", "ci_low", "ci_high",
                    "conf_part_mean", "shrinkage", "sign_same", "support_ok", "ci_excludes_mean", "confirmed",
                    "gpt_confirmed", "claude_confirmed", "perm_p_conf"]
            L.append(md(pre[cols], 4))
        else:
            L.append("_(no eligible rule to register)_\n")
    L.append("## 4. k of m per table\n")
    L.append(md(pd.DataFrame([{"table": f"et_{k}", "confirmed (k)": v["k"], "rows (m)": v["m"]} for k, v in per_table.items()])))
    for k in per_table:
        f = out / f"et_{k}_confirm.csv"
        t = read_et(f) if f.exists() else pd.DataFrame()
        if not len(t):
            continue
        L.append(f"\n**et_{k}** on confirmation\n")
        L.append(md(t[["step", "rule", "support_disc", "dev_disc", "support_conf", "dev_conf", "ci_low", "ci_high",
                       "shrinkage", "confirmed", "perm_p_conf"]], 4))
    L.append("\n## 5. Confirmed rules recomputed on all S2 items of their scope (worst first)\n")
    L.append("Points = deviation × 100 in the scope target (corpus: theme-centred score_rel; theme: absolute score). "
             "Percent = deviation / mean of the clipped score of the scope's S2 items. `clipped` = score in [0,1], "
             "`raw` = unclipped score. Worst axis: " + summ["worst_axis_definition"] + ".\n")
    for sc in scopes:
        ft = finals[sc["key"]]
        s = summ["scopes"][sc["key"]]
        L.append(f"### {sc['label']} (n = {s['n_all_s2']}; clipped means gpt {s['means_clipped']['gpt']:.4f}, "
                 f"claude {s['means_clipped']['claude']:.4f}, mean {s['means_clipped']['mean']:.4f})\n")
        if not len(ft):
            L.append("_(no confirmed rule)_\n"); continue
        show = ft[["rule", "preregistered_id", "confirmed_in", "n_disc", "n_conf", "n_all_s2", "themes",
                   "mean_target_dev_pts", "mean_target_dev_pct", "gpt_target_dev_pts", "claude_target_dev_pts",
                   "mean_clipped_dev_pts", "mean_raw_dev_pts", "mean_raw_dev_pct", "worst_axis", "worst_axis_term_pts",
                   "worst_axis_n"]].copy()
        L.append(md(show, 2))
    L.append("\n## 6. Judgement\n\n_[to be written after reading the outputs]_\n")
    (out / "REPORT_subset_s2.md").write_text("\n".join(L))
    log(f"report written: {out / 'REPORT_subset_s2.md'}")


if __name__ == "__main__":
    run(Path(sys.argv[1]))
