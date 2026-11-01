// Check the browser explanation-table search (demo/js/et.js) against the Python tables.
//   .venv/bin/python demo/tests/make_expected.py && node demo/tests/check_et.mjs
// Exit code 1 on any mismatch in a row's conditions, support or deviation, or in the
// candidate / eligible counts.
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const demo = path.resolve(here, "..");
const ctx = { window: {}, console, performance };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(demo, "data/corpus.js"), "utf8"), ctx);
vm.runInContext(fs.readFileSync(path.join(demo, "js/et.js"), "utf8"), ctx);
const D = ctx.window.SLICE_DATA, SL = ctx.window.SL;
const cases = JSON.parse(fs.readFileSync(path.join(demo, "data/test_expected.json"), "utf8"));
const EXCLUDE = new Set([...D.exclude.always, ...D.exclude.absence]);

let failures = 0;
for (const cs of cases) {
  const rows = [];
  const themeCodes = D.cols.theme.codes, themes = D.cols.theme.values;
  for (let i = 0; i < D.ids.length; i++) if (cs.theme === null || themes[themeCodes[i]] === cs.theme) rows.push(i);
  const n = rows.length;
  const cols = cs.cols.map((c) => ({ col: c, values: D.cols[c].values, codes: Int32Array.from(rows, (i) => D.cols[c].codes[i]) }));
  const y = Float64Array.from(rows, (i) => D.num[cs.target][i]);
  const res = SL.et.search({ n, cols, y, maxConj: cs.max_conj, minSupport: cs.min_support, minEffect: cs.min_effect,
                             maxRows: cs.max_rows, exclude: EXCLUDE, direction: "both", sameDirection: false });
  const problems = [];
  if (n !== cs.n) problems.push(`n ${n} != ${cs.n}`);
  if (res.nCandidates !== cs.n_candidates) problems.push(`candidates ${res.nCandidates} != ${cs.n_candidates}`);
  if (res.nEligible !== cs.n_eligible) problems.push(`eligible ${res.nEligible} != ${cs.n_eligible}`);
  if (res.rows.length !== cs.rows.length) problems.push(`rows ${res.rows.length} != ${cs.rows.length}`);
  const key = (conds) => conds.map(([a, v]) => `${a}=${v}`).sort().join(" & ");
  for (let r = 0; r < Math.min(res.rows.length, cs.rows.length); r++) {
    const got = res.rows[r], exp = cs.rows[r];
    const gk = key(got.pattern.map(([ci, v]) => [cs.cols[ci], v]));
    const ek = key(exp.conds);
    const dev = 100 * got.dev;
    if (gk !== ek || got.support !== exp.n || Math.abs(dev - exp.dev_pts) > 1e-6)
      problems.push(`row ${r + 1}: got ${gk} n=${got.support} dev=${dev.toFixed(4)} | expected ${ek} n=${exp.n} dev=${exp.dev_pts.toFixed(4)}`);
  }
  const status = problems.length ? "FAIL" : "ok  ";
  if (problems.length) failures++;
  console.log(`${status} ${cs.version} ${cs.table.padEnd(42)} n=${n} rows=${res.rows.length} cand=${res.nCandidates} elig=${res.nEligible} ${res.ms.toFixed(0)} ms`);
  for (const p of problems) console.log("       " + p);
}
console.log(failures ? `${failures} table(s) differ` : `all ${cases.length} tables reproduced row for row`);
process.exit(failures ? 1 : 0);
