/* Data layer: typed columns, scopes, labels. Reads window.SLICE_DATA (demo/data/corpus.js). */
(function (root) {
  "use strict";
  const SL = (root.SL = root.SL || {});
  const D = root.SLICE_DATA;
  if (!D) return;

  const A = {};
  D.attributes.forEach((a, i) => {
    a.order = i;
    a.valueBy = {};
    a.values.forEach((v) => { a.valueBy[v.raw] = v; });
    A[a.col] = a;
  });
  const themeBy = {};
  D.themes.forEach((t) => { themeBy[t.key] = t; });
  const modelName = { gpt: "GPT-5.5", claude: "Claude Opus 4.7", mean: "both models" };

  const num = {};
  for (const [k, arr] of Object.entries(D.num)) num[k] = Float64Array.from(arr, (v) => (v === null ? NaN : v));
  const codes = {};
  for (const [c, v] of Object.entries(D.cols)) codes[c] = Int32Array.from(v.codes);
  const universal = D.attributes.filter((a) => a.group === "universal").map((a) => a.col);
  const themeAttrs = D.attributes.filter((a) => a.group === "theme").map((a) => a.col);

  const scopes = new Map();
  function scope(key) {
    if (scopes.has(key)) return scopes.get(key);
    const theme = key === "corpus" ? null : key;
    const tv = D.cols.theme.values;
    const rows = [];
    for (let i = 0; i < D.ids.length; i++) if (!theme || tv[codes.theme[i]] === theme) rows.push(i);
    const t = theme ? themeBy[theme] : null;
    const sc = {
      key, theme, rows: Int32Array.from(rows), n: rows.length,
      family: theme ? "score" : "score_rel",
      name: theme ? t.name : "All themes",
      short: theme ? t.short : "All themes",
      cols: theme ? universal.concat(t.theme_attrs ? themeAttrs : []) : universal.concat(["theme"]),
      defaults: D.defaults[theme ? "theme" : "corpus"],
      ref: theme ? `the ${t.name} average` : "their theme average",
      _codes: {}, _num: {}, _means: {},
    };
    scopes.set(key, sc);
    return sc;
  }
  function localCodes(sc, col) {
    if (!sc._codes[col]) sc._codes[col] = Int32Array.from(sc.rows, (i) => codes[col][i]);
    return sc._codes[col];
  }
  function localNum(sc, name) {
    if (!sc._num[name]) sc._num[name] = Float64Array.from(sc.rows, (i) => num[name][i]);
    return sc._num[name];
  }
  /* mean over the scope, ignoring NaN */
  function scopeMean(sc, name) {
    if (sc._means[name] === undefined) {
      const a = localNum(sc, name);
      let s = 0, k = 0;
      for (let i = 0; i < a.length; i++) if (!isNaN(a[i])) { s += a[i]; k++; }
      sc._means[name] = k ? s / k : NaN;
    }
    return sc._means[name];
  }
  /* mean over local row indices, ignoring NaN; returns [mean, count] */
  function meanIdx(arr, idx) {
    let s = 0, k = 0;
    for (let t = 0; t < idx.length; t++) { const v = arr[idx[t]]; if (!isNaN(v)) { s += v; k++; } }
    return [k ? s / k : NaN, k];
  }
  /* local row indices of a pattern [[col, raw], ...] in a scope */
  function indexOf(sc, conds) {
    const out = [];
    const cs = conds.map(([c, v]) => [localCodes(sc, c), D.cols[c].values.indexOf(v)]);
    for (let i = 0; i < sc.n; i++) {
      let ok = true;
      for (const [cc, vi] of cs) if (cc[i] !== vi) { ok = false; break; }
      if (ok) out.push(i);
    }
    return Int32Array.from(out);
  }

  const label = (col, raw) => (A[col] && A[col].valueBy[raw] ? A[col].valueBy[raw].label : String(raw).replace(/_/g, " "));
  const phrase = (col, raw) => (A[col] && A[col].valueBy[raw] ? A[col].valueBy[raw].phrase : `${A[col] ? A[col].name.toLowerCase() : col} is ${raw}`);
  const attrName = (col) => (A[col] ? A[col].name : col);
  const isAbsence = (raw) => D.exclude.absence.includes(raw);
  const isExcluded = (raw) => D.exclude.always.includes(raw);
  const byOrder = (a, b) => A[a[0]].order - A[b[0]].order;

  SL.data = { D, A, themeBy, num, codes, universal, themeAttrs, modelName, scope, localCodes, localNum, scopeMean,
              meanIdx, indexOf, label, phrase, attrName, isAbsence, isExcluded, byOrder };
})(window);
