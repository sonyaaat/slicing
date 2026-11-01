"""Steps 1 and 2 of the v5 corpus run.

Step 1  corpus_data.csv, corpus_criteria.csv: all 4,027 matched-English conversations, every
        theme. Same extraction and integrity checks as the UC1 step 1 (step1_data.py), with
        the theme filter removed and a `theme` column added. Relative scores:
            score_rel_<m>  = score_<m>  - mean(score_<m>  | theme)      m in gpt, claude, mean
            score_rel_diff = score_diff_raw - mean(score_diff_raw | theme)
            axis_rel_<a>_<m> likewise for the five axes, m in gpt, claude, mean, diff
        Theme means are taken over all 4,027 rows (spec, steps 1-2).
Step 2  split_corpus.csv: 60/40, stratified by theme x quartile of the step-0 target within
        the theme, seed 42. The confirmation split is not read by anything before step 7.

Theme run (data.reuse_from, data.theme in the config): steps 1 and 2 copy the theme's rows of
the corpus run's three files unchanged instead, so the theme run keeps that run's scores and
its discovery / confirmation split.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import tiktoken
from scipy import stats
from sklearn.model_selection import train_test_split

from common import REPO_ROOT, UC1_ROOT, Run, die, log, write_json, write_meta
from step1_data import _text_of
from v5_infra import decide

MODELS = ("gpt", "claude")


def _read_log(path, id_set: set, sep: str, theme_prefix: str):
    from inspect_ai.log import read_eval_log_samples
    rows, crit = [], []
    for s in read_eval_log_samples(str(path), all_samples_required=False):
        pid = s.metadata.get("prompt_id", s.id)
        if pid not in id_set:
            continue
        tags = list((s.metadata or {}).get("example_tags") or [])
        themes = [t[len(theme_prefix):] for t in tags if t.startswith(theme_prefix)]
        if len(themes) != 1:
            die(f"{pid}: {len(themes)} theme tags")
        sc = next(iter(s.scores.values()))
        md = sc.metadata or {}
        user_msgs = [_text_of(m.content) for m in s.input if m.role == "user"]
        rows.append({"prompt_id": pid, "theme": themes[0], "tags": tags,
                     "user_text": sep.join(user_msgs), "n_user_turns": len(user_msgs),
                     "score_raw": sc.value["healthbench_score"]})
        for i, c in enumerate(md.get("detailed_results") or []):
            axes = [t.split(":", 1)[1] for t in (c.get("tags") or []) if t.startswith("axis:")]
            crit.append({"prompt_id": pid, "criterion_id": f"c{i:02d}",
                         "axis": axes[0] if len(axes) == 1 else ("|".join(axes) or None),
                         "n_axis_tags": len(axes), "points": c["points"], "met": c["met"],
                         "signature": f"{c['criterion']}\x1f{c['points']}\x1f"
                                      f"{'|'.join(sorted(c.get('tags') or []))}"})
    return pd.DataFrame(rows), pd.DataFrame(crit)


def step1(run: Run) -> None:
    cfg = run.cfg
    d = cfg["data"]
    if d.get("reuse_from"):
        return step1_reuse(run)
    lo, hi = cfg["scores"]["clip"]
    matched = {m: pd.read_csv(REPO_ROOT / d["matched_csv"][m]) for m in MODELS}
    id_set = set(matched["gpt"].prompt_id)
    if id_set != set(matched["claude"].prompt_id):
        die("main_data CSVs do not hold the same prompt_id set")
    frames, crits = {}, {}
    for m in MODELS:
        log(f"reading {d['eval_logs'][m]} ...")
        frames[m], crits[m] = _read_log(REPO_ROOT / d["eval_logs"][m], id_set,
                                        d["user_turn_separator"], d["theme_prefix"])
        log(f"  {m}: {len(frames[m])} rows, {len(crits[m])} criterion grades")

    checks: dict = {}
    g, c = frames["gpt"].set_index("prompt_id"), frames["claude"].set_index("prompt_id")
    if set(g.index) != set(c.index):
        die("the two logs give different prompt_id sets")
    if len(g) != d["expected_rows"]:
        die(f"{len(g)} rows, expected {d['expected_rows']}")
    c = c.loc[g.index]
    checks["rows"] = len(g)
    same_text = int((g.user_text == c.user_text).sum())
    checks["user_text_identical"] = f"{same_text}/{len(g)}"
    if same_text != len(g):
        die(f"user_text differs between logs on {len(g) - same_text} rows")
    same_theme = int((g.theme == c.theme).sum())
    checks["theme_identical"] = f"{same_theme}/{len(g)}"
    if same_theme != len(g):
        die("theme differs between logs")
    if g.theme.nunique() != d["expected_themes"]:
        die(f"{g.theme.nunique()} themes, expected {d['expected_themes']}")
    sig = {m: crits[m].groupby("prompt_id").signature.apply(tuple) for m in MODELS}
    same_rubric = int((sig["gpt"].loc[g.index] == sig["claude"].loc[g.index]).sum())
    checks["rubric_identical"] = f"{same_rubric}/{len(g)}"
    if same_rubric != len(g):
        die(f"rubric differs between logs on {len(g) - same_rubric} rows")
    checks["criteria_without_exactly_one_axis"] = int((crits["gpt"].n_axis_tags != 1).sum())
    for m, fr in (("gpt", g), ("claude", c)):
        ref = matched[m].set_index("prompt_id").loc[fr.index, "healthbench_score"]
        diff = float((fr.score_raw - ref).abs().max())
        checks[f"score_maxabsdiff_vs_main_data_{m}"] = diff
        if diff > 1e-9:
            die(f"{m}: log score differs from main_data by {diff}")

    cr_all = []
    for m in MODELS:
        cr = crits[m].copy()
        cr["pos"] = cr.points.where(cr.points > 0, 0)
        cr["ach"] = cr.points.where(cr.met == True, 0)  # noqa: E712
        cr["model"] = m
        cr_all.append(cr)
        re_ = cr.groupby("prompt_id").agg(pos=("pos", "sum"), ach=("ach", "sum"))
        re_score = (re_.ach / re_.pos).loc[g.index]
        fr = g if m == "gpt" else c
        diff = float((re_score - fr.score_raw).abs().max())
        checks[f"recomputed_score_maxabsdiff_{m}"] = diff
        if diff > 1e-9:
            die(f"{m}: recomputed score differs from logged score by {diff}")
    crit = pd.concat(cr_all, ignore_index=True)

    enc = tiktoken.get_encoding(d["tokenizer"])
    out = pd.DataFrame(index=g.index)
    out["theme"] = g.theme
    out["user_text"] = g.user_text
    out["n_user_turns"] = g.n_user_turns
    out["user_tokens"] = g.user_text.map(lambda t: len(enc.encode(t)))
    out["score_gpt_raw"] = g.score_raw
    out["score_claude_raw"] = c.score_raw
    out["score_gpt"] = g.score_raw.clip(lo, hi)
    out["score_claude"] = c.score_raw.clip(lo, hi)
    out["score_mean"] = (out.score_gpt + out.score_claude) / 2
    out["score_diff_raw"] = out.score_gpt_raw - out.score_claude_raw

    agg = crit.groupby(["prompt_id", "model", "axis"]).agg(pos=("pos", "sum"),
                                                          ach=("ach", "sum")).reset_index()
    agg["score"] = np.where(agg.pos > 0, agg.ach / agg.pos.where(agg.pos > 0), np.nan)
    for a in d["axes"]:
        for m in MODELS:
            s = agg[(agg.axis == a) & (agg.model == m)].set_index("prompt_id").score
            out[f"axis_{a}_{m}"] = s.reindex(out.index)
        out[f"axis_{a}_mean"] = (out[f"axis_{a}_gpt"] + out[f"axis_{a}_claude"]) / 2
        out[f"axis_{a}_diff"] = out[f"axis_{a}_gpt"] - out[f"axis_{a}_claude"]
    pts = agg.pivot_table(index=["prompt_id", "axis"], columns="model", values="ach",
                          fill_value=0)
    diff = (pts["gpt"] - pts["claude"]).unstack("axis").fillna(0)
    total_pos = crit[crit.model == "gpt"].groupby("prompt_id").pos.sum()
    contrib = diff.div(total_pos, axis=0).reindex(out.index)
    for a in d["axes"]:
        out[f"contrib_{a}"] = contrib[a] if a in contrib.columns else 0.0
    resid = (out[[f"contrib_{a}" for a in d["axes"]]].sum(axis=1)
             - (out.score_gpt_raw - out.score_claude_raw)).abs().max()
    checks["contrib_sum_maxabsdiff"] = float(resid)
    if resid > 1e-9:
        die(f"contrib does not sum to the raw score difference (max diff {resid})")

    # relative scores: minus the theme mean (over all 4,027 rows)
    for m in ("gpt", "claude", "mean"):
        out[f"score_rel_{m}"] = out[f"score_{m}"] - out.groupby("theme")[f"score_{m}"].transform("mean")
    out["score_rel_diff"] = out.score_diff_raw - out.groupby("theme").score_diff_raw.transform("mean")
    for a in d["axes"]:
        for m in ("gpt", "claude", "mean", "diff"):
            col = f"axis_{a}_{m}"
            out[f"axis_rel_{a}_{m}"] = out[col] - out.groupby("theme")[col].transform("mean")

    pref = d["physician_tag_prefix"]
    cats = g.tags.map(lambda t: [x[len(pref):] for x in t if x.startswith(pref)])
    if (cats.map(len) > 1).any():
        die("an item carries more than one physician_agreed_category")
    out["physician_category"] = cats.map(lambda l: l[0] if l else "none")
    out = out.reset_index().sort_values("prompt_id").reset_index(drop=True)
    out.to_csv(run.path("corpus_data.csv"), index=False)

    cw = crit.pivot_table(index=["prompt_id", "criterion_id"], columns="model", values="met",
                          aggfunc="first").reset_index()
    base = crit[crit.model == "gpt"][["prompt_id", "criterion_id", "axis", "points"]]
    cw = base.merge(cw, on=["prompt_id", "criterion_id"]).rename(
        columns={"gpt": "met_gpt", "claude": "met_claude"})
    cw.sort_values(["prompt_id", "criterion_id"]).to_csv(run.path("corpus_criteria.csv"),
                                                         index=False)
    checks["theme_counts"] = out.theme.value_counts().to_dict()
    checks["theme_mean_score_mean"] = out.groupby("theme").score_mean.mean().round(4).to_dict()
    checks["physician_category_none_by_theme"] = (
        out.assign(none=out.physician_category == "none").groupby("theme").none.mean()
        .round(3).to_dict())
    checks["n_criteria"] = int(len(cw))
    write_json(run.path("step1_checks.json"), checks)
    for f in ("corpus_data.csv", "corpus_criteria.csv"):
        write_meta(run, run.path(f), "1", integrity_checks=checks, api_calls=0)
    for k, v in checks.items():
        log(f"  {k}: {v}")


def step1_reuse(run: Run) -> None:
    d = run.cfg["data"]
    src, th = UC1_ROOT / d["reuse_from"], d["theme"]
    df = pd.read_csv(src / "corpus_data.csv")
    df = df[df.theme == th].reset_index(drop=True)
    if len(df) != d["expected_rows"]:
        die(f"{len(df)} rows of theme {th} in {src.name}, expected {d['expected_rows']}")
    cr = pd.read_csv(src / "corpus_criteria.csv")
    cr = cr[cr.prompt_id.isin(set(df.prompt_id))].reset_index(drop=True)
    if set(cr.prompt_id) != set(df.prompt_id):
        die("some rows of the theme have no criteria in the source run")
    df.to_csv(run.path("corpus_data.csv"), index=False)
    cr.to_csv(run.path("corpus_criteria.csv"), index=False)
    checks = {"reused_from": d["reuse_from"], "theme": th, "rows": len(df),
              "n_criteria": int(len(cr)),
              "theme_mean_score_mean": round(float(df.score_mean.mean()), 4)}
    write_json(run.path("step1_checks.json"), checks)
    for f in ("corpus_data.csv", "corpus_criteria.csv"):
        write_meta(run, run.path(f), "1", integrity_checks=checks, api_calls=0)
    for k, v in checks.items():
        log(f"  {k}: {v}")


def load_data(run: Run) -> pd.DataFrame:
    return pd.read_csv(run.path("corpus_data.csv"))


def step2_reuse(run: Run) -> None:
    d = run.cfg["data"]
    src = UC1_ROOT / d["reuse_from"]
    df = load_data(run)
    sp = pd.read_csv(src / "split_corpus.csv")
    sp = sp[sp.prompt_id.isin(set(df.prompt_id))].sort_values("prompt_id").reset_index(drop=True)
    if len(sp) != len(df) or (sp.theme != d["theme"]).any():
        die(f"split of {src.name} does not cover the {len(df)} rows of theme {d['theme']}")
    sp.to_csv(run.path("split_corpus.csv"), index=False)
    tgt = run.cfg["target"]
    m = df.set_index("prompt_id")[tgt]
    a = m[sp.loc[sp.split == "discovery", "prompt_id"]].dropna()
    b = m[sp.loc[sp.split == "confirmation", "prompt_id"]].dropna()
    ks = stats.ks_2samp(a, b)
    summ = {"target": tgt, "reused_from": d["reuse_from"],
            "counts": {s: int((sp.split == s).sum()) for s in ("discovery", "confirmation")},
            "ks_target": {"D": float(ks.statistic), "p": float(ks.pvalue)}}
    write_json(run.path("step2_split_summary.json"), summ)
    write_meta(run, run.path("split_corpus.csv"), "2", split_summary=summ, api_calls=0)
    log(f"split reused from {src.name}: {summ['counts']}; KS on {tgt}: "
        f"D={ks.statistic:.4f} p={ks.pvalue:.4f}")


def step2(run: Run) -> None:
    cfg = run.cfg
    if cfg["data"].get("reuse_from"):
        return step2_reuse(run)
    tgt = run.cfg["target"]
    if not tgt:
        die("no target in run_config.json - run step 0 first")
    df = load_data(run).sort_values("prompt_id").reset_index(drop=True)
    # quartile of the target within each theme, on the rank (ties broken by prompt_id order)
    q = pd.Series(index=df.index, dtype=object)
    for th, idx in df.groupby("theme").groups.items():
        sub = df.loc[idx, tgt]
        ok = sub.notna()
        if ok.sum():
            q.loc[sub[ok].index] = pd.qcut(sub[ok].rank(method="first"), 4,
                                           labels=False).astype(int).astype(str)
        q.loc[sub[~ok].index] = "na"
    df["stratum"] = df.theme + "|q" + q.astype(str)
    if (df.stratum.str.endswith("qna")).any():
        decide(run, "2", f"{int(df.stratum.str.endswith('qna').sum())} rows with no target value "
               "form their own stratum per theme", "the target is an axis score that is NaN "
               "where the rubric has no criterion on that axis")
    disc_idx, _ = train_test_split(df.index, train_size=cfg["split"]["discovery"],
                                   stratify=df.stratum, random_state=cfg["split"]["seed"])
    df["split"] = "confirmation"
    df.loc[disc_idx, "split"] = "discovery"
    df[["prompt_id", "theme", "stratum", "split"]].to_csv(run.path("split_corpus.csv"), index=False)

    summ: dict = {"target": tgt, "seed": cfg["split"]["seed"],
                  "counts": {s: int((df.split == s).sum()) for s in ("discovery", "confirmation")},
                  "by_theme": df.groupby(["theme", "split"]).size().unstack().to_dict("index")}
    # balance check on the stratification variable only (no attribute is defined yet)
    a = df.loc[df.split == "discovery", tgt].dropna()
    b = df.loc[df.split == "confirmation", tgt].dropna()
    ks = stats.ks_2samp(a, b)
    summ["ks_target"] = {"D": float(ks.statistic), "p": float(ks.pvalue)}
    write_json(run.path("step2_split_summary.json"), summ)
    write_meta(run, run.path("split_corpus.csv"), "2", split_summary=summ, api_calls=0)
    log(f"split: {summ['counts']}; KS on {tgt}: D={ks.statistic:.4f} p={ks.pvalue:.4f}")
    for th, v in summ["by_theme"].items():
        log(f"  {th:22s} discovery {v['discovery']:4d}  confirmation {v['confirmation']:4d}")


def discovery_frame(run: Run) -> pd.DataFrame:
    """Discovery rows only, with aliases p0001..; the confirmation split is dropped here."""
    df = load_data(run)
    sp = pd.read_csv(run.path("split_corpus.csv"))
    ids = set(sp.loc[sp.split == "discovery", "prompt_id"])
    d = df[df.prompt_id.isin(ids)].sort_values("prompt_id").reset_index(drop=True)
    pref = run.cfg["discovery"]["alias_prefix"]
    d["alias"] = [f"{pref}{i + 1:04d}" for i in range(len(d))]
    return d


def theme_sample(d: pd.DataFrame, n: int, seed: int) -> list[str]:
    """n prompt_ids stratified by theme with equal allocation (spec: ~43 per theme)."""
    themes = sorted(d.theme.unique())
    base, extra = divmod(n, len(themes))
    rng = np.random.default_rng(seed)
    out = []
    for i, th in enumerate(themes):
        k = base + (1 if i < extra else 0)
        pool = d.loc[d.theme == th, "prompt_id"].to_numpy()
        out += rng.choice(pool, size=min(k, len(pool)), replace=False).tolist()
    return sorted(out)
