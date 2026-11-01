/* Greedy explanation table, in the browser.
 *
 * Port of sliceability_uc1/code/v5_tables.fit_table (itself et.fit_table with boolean masks):
 *   candidates  every pattern of 1..maxConj attribute=value conditions, attributes distinct,
 *               values in `exclude` never used; same enumeration order as Python
 *               (k ascending, itertools.combinations of attributes, product of sorted values)
 *   eligible    support >= minSupport and |mean(pattern) - mean(all)| >= minEffect, on the
 *               target rescaled to [0, 1] with the scope min/max
 *   greedy      next row = argmax support * KL_Bernoulli(observed mean || model estimate),
 *               the model being the max-entropy logistic model refitted after every row
 *               (ridge 1e-6); stop when the gain is < 1e-9 or maxRows rows are chosen.
 * The refit uses Newton's method on rows grouped by pattern membership instead of L-BFGS-B:
 * the objective is convex, so both reach the same optimum. demo/tests/check_et.mjs checks
 * the result row for row against the tables the paper reports.
 *
 * Two options exist only here (both off when reproducing the paper): `direction` keeps only
 * worse or only better patterns, `sameDirection` keeps patterns where both models deviate
 * the same way.
 */
(function (root) {
  "use strict";
  const SL = (root.SL = root.SL || {});
  const EPS = 1e-12;

  function clip(p) { return p < EPS ? EPS : p > 1 - EPS ? 1 - EPS : p; }
  function kl(p, q) {
    p = clip(p); q = clip(q);
    return p * Math.log(p / q) + (1 - p) * Math.log((1 - p) / (1 - q));
  }
  function sigmoid(z) { return z >= 0 ? 1 / (1 + Math.exp(-z)) : Math.exp(z) / (1 + Math.exp(z)); }
  function softplus(z) { return z > 0 ? z + Math.log1p(Math.exp(-z)) : Math.log1p(Math.exp(z)); }

  /* sorted Int32Array intersection */
  function intersect(a, b) {
    const out = new Int32Array(Math.min(a.length, b.length));
    let i = 0, j = 0, k = 0;
    while (i < a.length && j < b.length) {
      const x = a[i], y = b[j];
      if (x === y) { out[k++] = x; i++; j++; } else if (x < y) i++; else j++;
    }
    return out.subarray(0, k);
  }

  function* combinations(n, k, start = 0, prefix = []) {
    if (prefix.length === k) { yield prefix.slice(); return; }
    for (let i = start; i <= n - (k - prefix.length); i++) {
      prefix.push(i);
      yield* combinations(n, k, i + 1, prefix);
      prefix.pop();
    }
  }

  function meanOf(arr, idx) {
    let s = 0;
    for (let t = 0; t < idx.length; t++) s += arr[idx[t]];
    return s / idx.length;
  }

  /* Solve H x = g for symmetric positive-definite H (d x d, flat). */
  function cholSolve(H, g, d) {
    const L = new Float64Array(d * d);
    for (let i = 0; i < d; i++) {
      for (let j = 0; j <= i; j++) {
        let s = H[i * d + j];
        for (let k = 0; k < j; k++) s -= L[i * d + k] * L[j * d + k];
        if (i === j) L[i * d + i] = Math.sqrt(Math.max(s, 1e-300));
        else L[i * d + j] = s / L[j * d + j];
      }
    }
    const z = new Float64Array(d);
    for (let i = 0; i < d; i++) {
      let s = g[i];
      for (let k = 0; k < i; k++) s -= L[i * d + k] * z[k];
      z[i] = s / L[i * d + i];
    }
    const x = new Float64Array(d);
    for (let i = d - 1; i >= 0; i--) {
      let s = z[i];
      for (let k = i + 1; k < d; k++) s -= L[k * d + i] * x[k];
      x[i] = s / L[i * d + i];
    }
    return x;
  }

  /* Max-entropy logistic model: minimise sum softplus(z) - y z + ridge/2 |b[1:]|^2 with
   * z = b0 + sum_j b_j [row in pattern j]. Rows with the same membership share z, so the
   * fit runs on groups. Returns {beta, u} with u = fitted probability per row. */
  function fitLogistic(y, sets, n, init, ridge) {
    const d = sets.length + 1;
    const mem = new Uint32Array(n);
    sets.forEach((idx, j) => { for (let t = 0; t < idx.length; t++) mem[idx[t]] |= (1 << j); });
    const gIndex = new Map();
    const gMem = [], gN = [], gY = [];
    for (let i = 0; i < n; i++) {
      let g = gIndex.get(mem[i]);
      if (g === undefined) { g = gMem.length; gIndex.set(mem[i], g); gMem.push(mem[i]); gN.push(0); gY.push(0); }
      gN[g] += 1; gY[g] += y[i];
    }
    const G = gMem.length;
    const bits = gMem.map((m) => { const b = []; for (let j = 0; j < sets.length; j++) if (m & (1 << j)) b.push(j + 1); return b; });
    let b = new Float64Array(d);
    if (init && init.length) { for (let j = 0; j < Math.min(init.length, d); j++) b[j] = init[j]; }
    else { let s = 0; for (let i = 0; i < n; i++) s += y[i]; const m = clip(s / n); b[0] = Math.log(m / (1 - m)); }

    const zOf = (bb, g) => { let z = bb[0]; for (const j of bits[g]) z += bb[j]; return z; };
    const lossOf = (bb) => {
      let L = 0;
      for (let g = 0; g < G; g++) { const z = zOf(bb, g); L += gN[g] * softplus(z) - z * gY[g]; }
      for (let j = 1; j < d; j++) L += 0.5 * ridge * bb[j] * bb[j];
      return L;
    };
    let loss = lossOf(b);
    for (let it = 0; it < 100; it++) {
      const grad = new Float64Array(d), H = new Float64Array(d * d);
      for (let g = 0; g < G; g++) {
        const p = sigmoid(zOf(b, g));
        const r = gN[g] * p - gY[g], w = gN[g] * p * (1 - p);
        const act = [0].concat(bits[g]);
        for (const a of act) {
          grad[a] += r;
          for (const c of act) H[a * d + c] += w;
        }
      }
      let gmax = 0;
      for (let j = 1; j < d; j++) { grad[j] += ridge * b[j]; H[j * d + j] += ridge; }
      for (let j = 0; j < d; j++) gmax = Math.max(gmax, Math.abs(grad[j]));
      if (gmax < 1e-10) break;
      const step = cholSolve(H, grad, d);
      let dec = 0;
      for (let j = 0; j < d; j++) dec += grad[j] * step[j];
      let t = 1, nb, nl;
      for (let ls = 0; ls < 60; ls++) {
        nb = new Float64Array(d);
        for (let j = 0; j < d; j++) nb[j] = b[j] - t * step[j];
        nl = lossOf(nb);
        if (nl <= loss - 1e-4 * t * dec || nl <= loss) break;
        t *= 0.5;
      }
      const done = Math.abs(loss - nl) < 1e-15 * Math.max(1, Math.abs(loss));
      b = nb; loss = nl;
      if (done) break;
    }
    const pg = new Float64Array(G);
    for (let g = 0; g < G; g++) pg[g] = sigmoid(zOf(b, g));
    const u = new Float64Array(n);
    for (let i = 0; i < n; i++) u[i] = pg[gIndex.get(mem[i])];
    return { beta: b, u };
  }

  /*
   * opts:
   *   n                rows in scope
   *   cols             [{col, codes: Int32Array(n) (-1 = missing), values: [raw strings]}], in search order
   *   y                Float64Array(n): target, raw units
   *   yA, yB           optional Float64Array(n): per-model targets (landscape, sameDirection)
   *   maxConj, minSupport, minEffect (raw units), maxRows, exclude (Set of raw values)
   *   direction        "both" | "worse" | "better"
   *   sameDirection    bool
   * returns {rows, candidates, nCandidates, nEligible, gmean, lo, hi, ms}
   *   rows[i]       {step, pattern: [[colIndex, valueString]], idx, support, mean, dev, gain}
   *   candidates    every pattern with support >= minSupport: {pattern, idx, support, dev, devA, devB, eligible}
   */
  function search(o) {
    const t0 = (typeof performance !== "undefined" ? performance : Date).now();
    const n = o.n, yRaw = o.y;
    let lo = Infinity, hi = -Infinity;
    for (let i = 0; i < n; i++) { if (yRaw[i] < lo) lo = yRaw[i]; if (yRaw[i] > hi) hi = yRaw[i]; }
    const span = hi - lo || 1;
    const y = new Float64Array(n);
    let gs = 0;
    for (let i = 0; i < n; i++) { y[i] = (yRaw[i] - lo) / span; gs += y[i]; }
    const gmean = gs / n;
    const minEff = o.minEffect / span;
    const exclude = o.exclude || new Set();
    let mA = 0, mB = 0;
    if (o.yA) { for (let i = 0; i < n; i++) { mA += o.yA[i]; mB += o.yB[i]; } mA /= n; mB /= n; }

    // single conditions with enough support, values sorted as Python's sorted(set(...), key=str)
    const lists = o.cols.map((c) => {
      const present = new Set();
      for (let i = 0; i < n; i++) if (c.codes[i] >= 0) present.add(c.codes[i]);
      const vals = [...present].map((ci) => c.values[ci]).filter((v) => !exclude.has(v))
        .sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
      const out = [];
      for (const v of vals) {
        const vi = c.values.indexOf(v);
        const tmp = [];
        for (let i = 0; i < n; i++) if (c.codes[i] === vi) tmp.push(i);
        if (tmp.length >= o.minSupport) out.push({ value: v, idx: Int32Array.from(tmp) });
      }
      return out;
    });

    const candidates = [], eligible = [];
    let nCand = 0;
    const C = o.cols.length;
    for (let k = 1; k <= o.maxConj; k++) {
      for (const combo of combinations(C, k)) {
        const L = combo.map((ci) => lists[ci]);
        if (L.some((l) => l.length === 0)) continue;
        const restProd = new Array(k + 1).fill(1);
        for (let d = k - 1; d >= 0; d--) restProd[d] = restProd[d + 1] * L[d].length;
        const rec = (d, idx, pat) => {
          if (d === k) {
            nCand++;
            const support = idx.length;
            const mean = meanOf(y, idx);
            const dev = mean - gmean;
            const cand = { pattern: pat, idx, support, mean, dev: dev * span, eligible: false };
            if (o.yA) { cand.devA = meanOf(o.yA, idx) - mA; cand.devB = meanOf(o.yB, idx) - mB; }
            let ok = Math.abs(dev) >= minEff;
            if (ok && o.direction === "worse" && !(dev < 0)) ok = false;
            if (ok && o.direction === "better" && !(dev > 0)) ok = false;
            if (ok && o.sameDirection && o.yA && Math.sign(cand.devA) !== Math.sign(cand.devB)) ok = false;
            cand.eligible = ok;
            candidates.push(cand);
            if (ok) eligible.push(cand);
            return;
          }
          const lst = L[d];
          for (let j = 0; j < lst.length; j++) {
            const nidx = d === 0 ? lst[j].idx : intersect(idx, lst[j].idx);
            if (nidx.length < o.minSupport) { nCand += restProd[d + 1]; continue; }
            rec(d + 1, nidx, pat.concat([[combo[d], lst[j].value]]));
          }
        };
        rec(0, null, []);
      }
    }

    // greedy selection
    const E = eligible.length;
    const taken = new Uint8Array(E);
    let u = new Float64Array(n).fill(gmean);
    let beta = null;
    const sel = [], rows = [];
    for (let step = 1; step <= o.maxRows && E; step++) {
      let best = -1, bestGain = -Infinity, bestEst = 0;
      for (let j = 0; j < E; j++) {
        if (taken[j]) continue;
        const c = eligible[j];
        const est = meanOf(u, c.idx);
        const gain = c.support * kl(c.mean, est);
        if (gain > bestGain) { bestGain = gain; best = j; bestEst = est; }
      }
      if (best < 0 || !isFinite(bestGain) || bestGain < 1e-9) break;
      taken[best] = 1;
      sel.push(best);
      const fit = fitLogistic(y, sel.map((j) => eligible[j].idx), n, beta, 1e-6);
      beta = fit.beta; u = fit.u;
      const c = eligible[best];
      c.step = step;
      rows.push({ step, pattern: c.pattern, idx: c.idx, support: c.support, mean: c.mean * span + lo,
                  dev: c.dev, gain: bestGain, estimateBefore: bestEst * span + lo });
    }
    const ms = (typeof performance !== "undefined" ? performance : Date).now() - t0;
    return { rows, candidates, nCandidates: nCand, nEligible: E, gmean: gmean * span + lo, lo, hi, ms };
  }

  /* Two-sided permutation p of a slice mean: P(|mean of a random same-size subset - mean| >= observed). */
  function permutationP(y, idx, nPerm, seed) {
    const n = y.length, k = idx.length;
    if (k === 0 || k >= n) return NaN;
    let tot = 0;
    for (let i = 0; i < n; i++) tot += y[i];
    const m = tot / n;
    const obs = Math.abs(meanOf(y, idx) - m);
    let s = seed >>> 0 || 1;
    const rnd = () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
    const perm = new Int32Array(n);
    for (let i = 0; i < n; i++) perm[i] = i;
    let hits = 0;
    for (let r = 0; r < nPerm; r++) {
      let sum = 0;
      for (let t = 0; t < k; t++) {
        const j = t + Math.floor(rnd() * (n - t));
        const tmp = perm[t]; perm[t] = perm[j]; perm[j] = tmp;
        sum += y[perm[t]];
      }
      if (Math.abs(sum / k - m) >= obs - 1e-12) hits++;
    }
    return (hits + 1) / (nPerm + 1);
  }

  function bh(p) {
    const m = p.length;
    const order = p.map((v, i) => [v, i]).sort((a, b) => a[0] - b[0]);
    const adj = new Array(m);
    let prev = 1;
    for (let r = m; r >= 1; r--) {
      const [v, i] = order[r - 1];
      prev = Math.min(prev, (v * m) / r);
      adj[i] = prev;
    }
    return adj;
  }

  SL.et = { search, permutationP, bh, intersect, fitLogistic };
})(typeof window !== "undefined" ? window : globalThis);
