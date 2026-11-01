/* Slice model: runs the explanation-table search for a state and computes the statistics of a slice. */
(function (root) {
  "use strict";
  const SL = (root.SL = root.SL || {});
  const { D } = SL.data;
  const dat = SL.data;
  const MODELS = ["gpt", "claude", "mean"];

  const keyOf = (conds) => conds.map(([c, v]) => `${c}=${v}`).sort().join("|");

  /* attributes searched in a scope: the universal ones, plus the theme's own in Emergency
   * referrals; never the theme itself; minus the ones switched off in the Attributes panel */
  function activeCols(st, sc) {
    return sc.cols.filter((c) => c !== "theme" && !st.off.includes(c));
  }
  /* values never used in a rule: other / unknown / not applicable / parse error, and the
   * absence values ("not stated"): a slice is described by what a message says */
  function excludeSet() {
    return new Set(D.exclude.always.concat(D.exclude.absence));
  }

  /* n, share, and per model: deviation from the scope mean (score units), as a share of the
   * scope's mean score, and the slice's mean score */
  function stats(sc, idx, st) {
    const fam = sc.family;
    const out = { n: idx.length, share: idx.length / sc.n, dev: {}, pct: {}, abs: {}, absScope: {} };
    for (const m of MODELS) {
      const [mu] = dat.meanIdx(dat.localNum(sc, `${fam}_${m}`), idx);
      out.dev[m] = mu - dat.scopeMean(sc, `${fam}_${m}`);
      out.absScope[m] = dat.scopeMean(sc, `score_${m}`);
      out.abs[m] = dat.meanIdx(dat.localNum(sc, `score_${m}`), idx)[0];
      out.pct[m] = out.dev[m] / out.absScope[m];
    }
    const t = st ? st.target : "mean";
    out.devT = out.dev[t]; out.pctT = out.pct[t];
    return out;
  }

  const cache = new Map();
  function searchKey(st) {
    return [st.scope, st.target, st.dir, st.k, st.sup, st.conj, st.eff, st.off.slice().sort().join(",")].join("/");
  }
  function search(st) {
    const key = searchKey(st);
    if (cache.has(key)) return cache.get(key);
    const sc = dat.scope(st.scope);
    const cols = activeCols(st, sc);
    const fam = sc.family;
    const res = SL.et.search({
      n: sc.n,
      cols: cols.map((c) => ({ col: c, values: D.cols[c].values, codes: dat.localCodes(sc, c) })),
      y: dat.localNum(sc, `${fam}_${st.target}`),
      yA: dat.localNum(sc, `${fam}_gpt`), yB: dat.localNum(sc, `${fam}_claude`),
      maxConj: st.conj, minSupport: st.sup, minEffect: st.eff, maxRows: st.k,
      exclude: excludeSet(), direction: st.dir, sameDirection: false,
    });
    res.scope = sc;
    res.rows.forEach((r) => {
      r.conds = r.pattern.map(([ci, v]) => [cols[ci], v]).sort(dat.byOrder);
      Object.assign(r, stats(sc, r.idx, st));
    });
    res.worse = res.rows.filter((r) => r.devT < 0).sort((a, b) => a.devT - b.devT);
    res.better = res.rows.filter((r) => r.devT >= 0).sort((a, b) => b.devT - a.devT);
    res.maxPct = Math.max(0.05, ...res.rows.flatMap((r) => [Math.abs(r.pct.gpt), Math.abs(r.pct.claude)]));
    cache.set(key, res);
    if (cache.size > 60) cache.delete(cache.keys().next().value);
    return res;
  }

  SL.model = { keyOf, activeCols, stats, search, MODELS };
})(window);
