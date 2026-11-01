"""Greedy explanation table for a target in [0, 1].

Port of the repository's GreedyExplanationTable (explanation_table.py at the repo root),
which is left untouched. The algorithm is the same - candidate patterns of up to
max_conj attribute=value conditions, a maximum-entropy logistic model refitted after
every addition, and the next row chosen by information gain
    gain(p) = support(p) * KL_Bernoulli(observed mean in p || model's estimate in p).
The only change is that the outcome may be any value in [0, 1], not just 0/1. Both the
gain and the logistic objective are cross-entropies, which are well defined for a
fractional outcome; that is the reason the spec clips scores to [0, 1].

The spec's two row rules are applied as candidate eligibility before the greedy loop:
    support >= min_support   and   |mean(p) - mean(all)| >= min_effect
The table then holds up to max_rows such rows (the all-rows baseline is not counted).
"""

from __future__ import annotations

import itertools

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit


def _bern_kl(p, q, eps=1e-12):
    p = np.clip(p, eps, 1 - eps); q = np.clip(q, eps, 1 - eps)
    return p * np.log(p / q) + (1 - p) * np.log((1 - p) / (1 - q))


def _total_ce(y, u, eps=1e-12):
    u = np.clip(u, eps, 1 - eps)
    return float(np.sum(y * np.log(1 / u) + (1 - y) * np.log(1 / (1 - u))))


def _fit(y, X, ridge=1e-6, init=None):
    if init is None or len(init) != X.shape[1]:
        b0 = np.zeros(X.shape[1])
        if init is not None:
            b0[:len(init)] = init[:X.shape[1]]
        else:
            b0[0] = logit(np.clip(y.mean(), 1e-6, 1 - 1e-6))
        init = b0

    def f(b):
        z = X @ b
        loss = np.sum(np.logaddexp(0, z) - y * z) + 0.5 * ridge * np.sum(b[1:] ** 2)
        g = X.T @ (expit(z) - y)
        g[1:] += ridge * b[1:]
        return loss, g

    r = minimize(lambda b: f(b)[0], init, jac=lambda b: f(b)[1], method="L-BFGS-B",
                 options={"maxiter": 1000})
    return r.x, expit(X @ r.x)


def candidates(values: dict[str, np.ndarray], max_conj: int, exclude=frozenset()):
    """All patterns: tuples of (attribute, value) of length 1..max_conj, attributes distinct.
    Values in `exclude` never appear in a pattern."""
    attrs = list(values)
    doms = {a: sorted(set(values[a].tolist()) - set(exclude), key=str) for a in attrs}
    out = []
    for k in range(1, max_conj + 1):
        for combo in itertools.combinations(attrs, k):
            for vals in itertools.product(*(doms[a] for a in combo)):
                out.append(tuple(zip(combo, vals)))
    return out


def mask_of(values: dict[str, np.ndarray], pattern) -> np.ndarray:
    n = len(next(iter(values.values())))
    m = np.ones(n, dtype=bool)
    for a, v in pattern:
        m &= values[a] == v
    return m


def fit_table(values: dict[str, np.ndarray], y: np.ndarray, *, max_conj: int,
              min_support: int, min_effect: float, max_rows: int, ridge: float = 1e-6,
              min_gain: float = 1e-9, exclude=frozenset()) -> dict:
    y = np.asarray(y, dtype=float)
    if y.min() < 0 or y.max() > 1:
        raise ValueError("target must lie in [0, 1]")
    n = len(y)
    gmean = float(y.mean())
    pats = candidates(values, max_conj, exclude)
    masks = np.array([mask_of(values, p) for p in pats], dtype=float)
    sup = masks.sum(axis=1)
    obs = (masks @ y) / np.where(sup > 0, sup, 1)
    elig = (sup >= min_support) & (np.abs(obs - gmean) >= min_effect)
    n_cand = len(pats)
    pats = [p for p, e in zip(pats, elig) if e]
    masks, sup, obs = masks[elig], sup[elig], obs[elig]

    rows = []
    u = np.full(n, gmean)
    ce = _total_ce(y, u)
    sel, beta = [], None
    taken = np.zeros(len(pats), dtype=bool)
    for step in range(1, max_rows + 1):
        if not len(pats):
            break
        est = (masks @ u) / sup
        gain = sup * _bern_kl(obs, est)
        gain[taken] = -np.inf
        i = int(np.argmax(gain))
        if not np.isfinite(gain[i]) or gain[i] < min_gain:
            break
        taken[i] = True
        sel.append(i)
        X = np.column_stack([np.ones(n)] + [masks[j] for j in sel])
        beta, u = _fit(y, X, ridge, beta)
        ce_new = _total_ce(y, u)
        rows.append({"step": step, "pattern": pats[i], "support": int(sup[i]),
                     "mean": float(obs[i]), "estimate_before": float(est[i]),
                     "gain": float(gain[i]), "cross_entropy_after": ce_new})
        ce = ce_new
    return {"rows": rows, "global_mean": gmean, "n": n, "n_candidates": n_cand,
            "n_eligible": int(len(pats)), "final_cross_entropy": ce}


def permutation_p(y: np.ndarray, mask: np.ndarray, n_perm: int, seed: int) -> float:
    """Two-sided: P(|mean of a random subset of the same size - mean| >= observed)."""
    y = np.asarray(y, dtype=float)
    k = int(mask.sum())
    obs = abs(y[mask].mean() - y.mean())
    rng = np.random.default_rng(seed)
    hits = 0
    done = 0
    while done < n_perm:
        b = min(2000, n_perm - done)
        idx = np.argsort(rng.random((b, len(y))), axis=1)[:, :k]
        means = y[idx].mean(axis=1)
        hits += int(np.sum(np.abs(means - y.mean()) >= obs - 1e-12))
        done += b
    return (hits + 1) / (n_perm + 1)


def bh(p: list[float]) -> list[float]:
    p = np.asarray(p, dtype=float)
    m = len(p)
    if m == 0:
        return []
    order = np.argsort(p)
    adj = np.empty(m)
    prev = 1.0
    for rank, i in reversed(list(enumerate(order, 1))):
        prev = min(prev, p[i] * m / rank)
        adj[i] = prev
    return adj.tolist()
