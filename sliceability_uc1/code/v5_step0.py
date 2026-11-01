"""Step 0 - explained variance of each target from the text alone, and the target choice.

1. bge-m3 embedding of every user_text (all 4,027; local model, normalised vectors).
2. Ridge regression embedding -> target, 5-fold CV (KFold, shuffled, seed 42). In every
   outer fold the ridge penalty is chosen by RidgeCV (efficient leave-one-out) on the
   training part only, so the held-out fold never influences alpha. R2 is computed on each
   held-out fold; r2_cv_mean is their mean (the decision metric), r2_oof is R2 of the pooled
   out-of-fold predictions. Rows with a NaN target (axis without a criterion) are left out
   for that target.
3. Partitions: the corpus and each theme. Within a theme the relative and raw targets
   differ by a constant, so raw overall scores are reported for the corpus only.

Decision (spec + run brief): among score_rel_mean, axis_rel_context_awareness_mean and
axis_rel_completeness_mean, the target is score_rel_mean unless an axis target beats it on
the corpus by >= step0.axis_margin; then the best such axis. Written to run_config.json.
"""

from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.metrics import r2_score
from sklearn.model_selection import KFold

from common import Run, log, write_json, write_meta
from v5_data import load_data
from v5_infra import decide


def targets(cfg) -> list[tuple[str, str]]:
    """(column, kind). kind: rel_overall / raw_overall / rel_axis."""
    out = [(f"score_rel_{m}", "rel_overall") for m in ("gpt", "claude", "mean", "diff")]
    out += [(f"score_{m}", "raw_overall") for m in ("gpt", "claude", "mean")]
    for a in cfg["data"]["axes"]:
        out += [(f"axis_rel_{a}_{m}", "rel_axis") for m in ("gpt", "claude", "mean")]
    return out


def embed(run: Run, df: pd.DataFrame) -> np.ndarray:
    path = run.path("embeddings_bge_m3.npy")
    ids_path = run.path("embeddings_bge_m3_ids.json")
    if path.exists() and ids_path.exists() and json.loads(ids_path.read_text()) == df.prompt_id.tolist():
        log("step 0: embeddings restored from checkpoint")
        return np.load(path)
    import torch
    from sentence_transformers import SentenceTransformer
    s0 = run.cfg["step0"]
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    m = SentenceTransformer(s0["embedding_model"], device=dev)
    m.max_seq_length = s0["max_seq_length"]
    t0 = time.time()
    emb = m.encode(df.user_text.tolist(), normalize_embeddings=True,
                   batch_size=s0["batch_size"], show_progress_bar=False)
    emb = np.asarray(emb, dtype=np.float32)
    np.save(path, emb)
    ids_path.write_text(json.dumps(df.prompt_id.tolist()))
    write_meta(run, path, "0", model=s0["embedding_model"], device=dev,
               max_seq_length=s0["max_seq_length"], seconds=round(time.time() - t0, 1),
               dim=int(emb.shape[1]))
    log(f"step 0: embedded {len(df)} texts on {dev} in {time.time() - t0:.0f}s, dim {emb.shape[1]}")
    return emb


def cv_r2(X: np.ndarray, y: np.ndarray, folds: int, seed: int, alphas) -> dict:
    kf = KFold(n_splits=folds, shuffle=True, random_state=seed)
    pred = np.empty_like(y)
    r2s, al = [], []
    for tr, te in kf.split(X):
        m = RidgeCV(alphas=alphas).fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
        r2s.append(r2_score(y[te], pred[te]))
        al.append(float(m.alpha_))
    return {"r2_cv_mean": float(np.mean(r2s)), "r2_cv_sd": float(np.std(r2s, ddof=1)),
            "r2_oof": float(r2_score(y, pred)), "alpha_median": float(np.median(al)),
            "r2_folds": [round(float(r), 4) for r in r2s]}


def run(run: Run) -> None:
    s0 = run.cfg["step0"]
    df = load_data(run).sort_values("prompt_id").reset_index(drop=True)
    tok = df.user_tokens.describe(percentiles=[.5, .9, .99]).round(0).to_dict()
    log(f"step 0: user_text tokens (o200k) {tok}")
    X = embed(run, df)
    rows = []
    parts = [("corpus", np.ones(len(df), dtype=bool))] + \
            [(f"theme:{t}", (df.theme == t).to_numpy()) for t in sorted(df.theme.unique())]
    for col, kind in targets(run.cfg):
        for pname, pm in parts:
            if kind == "raw_overall" and pname != "corpus":
                continue
            y = df[col].to_numpy(dtype=float)
            ok = pm & ~np.isnan(y)
            r = cv_r2(X[ok], y[ok], s0["cv_folds"], s0["cv_seed"], s0["ridge_alphas"])
            rows.append({"target": col, "kind": kind, "partition": pname, "n": int(ok.sum()),
                         "target_sd": float(np.std(y[ok], ddof=1)), **r})
        log(f"  {col:45s} corpus R2 = {rows[-(1 if kind == 'raw_overall' else 8)]['r2_cv_mean']:.4f}")
    tab = pd.DataFrame(rows)
    tab["r2_folds"] = tab.r2_folds.map(lambda x: " ".join(f"{v:.4f}" for v in x))
    tab.to_csv(run.path("step0_r2.csv"), index=False)

    corp = tab[tab.partition == "corpus"].set_index("target")
    cands = run.cfg["target_candidates"]
    metric = s0["decision_metric"]
    r2 = {c: float(corp.loc[c, metric]) for c in cands}
    base = s0["default_target"]
    axes = {c: v for c, v in r2.items() if c != base}
    best_axis = max(axes, key=axes.get)
    if axes[best_axis] - r2[base] >= s0["axis_margin"]:
        chosen = best_axis
        reason = (f"{best_axis} corpus {metric} {axes[best_axis]:.4f} beats {base} "
                  f"{r2[base]:.4f} by {axes[best_axis] - r2[base]:.4f} >= {s0['axis_margin']}")
    else:
        chosen = base
        reason = (f"{base} corpus {metric} {r2[base]:.4f}; best axis {best_axis} "
                  f"{axes[best_axis]:.4f} (margin {axes[best_axis] - r2[base]:+.4f} < "
                  f"{s0['axis_margin']}); candidates {json.dumps({k: round(v, 4) for k, v in r2.items()})}")
    if max(r2.values()) < 0.05:
        decide(run, "0", "low explained variance recorded as a result; discovery runs anyway",
               f"all candidate corpus R2 < 0.05 ({json.dumps({k: round(v, 4) for k, v in r2.items()})}); "
               "spec risk table: keep the best target, lower expectations")
    decide(run, "0", f"target = {chosen}", reason)
    cfg_path = run.path("run_config.json")
    cfg = json.loads(cfg_path.read_text())
    cfg["target"] = cfg["target_score"] = chosen
    cfg["target_family"] = chosen[:-len("_mean")]
    cfg["step0_result"] = {"candidates": r2, "chosen": chosen, "reason": reason}
    write_json(cfg_path, cfg)
    run.cfg = cfg
    write_meta(run, run.path("step0_r2.csv"), "0", decision=chosen, reason=reason, api_calls=0)
