// End-to-end smoke test of the demo UI in headless Chrome (DevTools protocol, no dependencies).
//   node demo/tests/ui_smoke.mjs [screenshot_dir]
// Clicks through every view, checks a few facts on screen, fails on any JavaScript error,
// and saves a screenshot per step (default: demo/data/screens/).
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const demo = path.resolve(here, "..");
const outDir = path.resolve(process.argv[2] || path.join(demo, "data/screens"));
fs.mkdirSync(outDir, { recursive: true });
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PORT = 9300 + Math.floor(Math.random() * 500);
const prof = fs.mkdtempSync(path.join(os.tmpdir(), "sl-chrome-"));
const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${prof}`, "--no-first-run",
  "--no-default-browser-check", "--hide-scrollbars", "--window-size=1680,1050", "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let ws, nextId = 1;
const pending = new Map(), errors = [], failures = [];
function send(method, params = {}) {
  const id = nextId++;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}
async function evaluate(expr) {
  const r = await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(`evaluate failed: ${expr.slice(0, 80)} :: ${r.exceptionDetails.exception?.description || r.exceptionDetails.text}`);
  return r.result.value;
}
async function shot(name, width = 1680, height = 1050) {
  await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
  await sleep(250);
  const r = await send("Page.captureScreenshot", { format: "png" });
  fs.writeFileSync(path.join(outDir, `${name}.png`), Buffer.from(r.data, "base64"));
}
function check(cond, msg) { if (!cond) failures.push(msg); console.log(`${cond ? "ok  " : "FAIL"} ${msg}`); }

async function main() {
  let ver;
  for (let i = 0; i < 60 && !ver; i++) { try { ver = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); } catch { await sleep(200); } }
  const page = ver.find((t) => t.type === "page");
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r));
  ws.addEventListener("message", (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(new Error(m.error.message)) : p.resolve(m.result); }
    if (m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
    if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") errors.push(m.params.args.map((a) => a.value || a.description).join(" "));
    if (m.method === "Log.entryAdded" && m.params.entry.level === "error") errors.push(`${m.params.entry.text} ${m.params.entry.url || ""}`);
  });
  await send("Page.enable"); await send("Runtime.enable"); await send("Log.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1680, height: 1050, deviceScaleFactor: 1, mobile: false });
  await send("Page.navigate", { url: "file://" + path.join(demo, "index.html") });
  await sleep(1500);

  // 1. the main screen: theme tabs, settings bar, table, nothing else
  check(await evaluate("document.querySelectorAll('tr.slice').length") === 10, "corpus table has 10 rows");
  const firstRow = await evaluate("document.querySelector('tr.slice').innerText");
  check(/inpatient or ER/.test(firstRow) && /worsening/.test(firstRow) && /−29%/.test(firstRow), "largest drop is inpatient or ER + worsening, −29%");
  check(await evaluate("!document.querySelector('#landscape, #slicecard, #confirmedcard, .switch, .tour')"), "removed parts are gone");
  check(await evaluate("document.querySelectorAll('.theme-tab').length") === 2, "2 tabs: All themes, Emergency referrals");
  check(await evaluate("!document.querySelector('.brand-sub, .top .lm')"), "header holds only the name and two buttons");
  await shot("01_main");
  await shot("01b_main_full", 1680, 1250);

  // 2. settings
  await evaluate("[...document.querySelectorAll('#controls .seg button')].find(b => b.textContent === 'GPT-5.5').click()");
  check(await evaluate("SL.state.get().target") === "gpt", "score of GPT-5.5");
  await evaluate("[...document.querySelectorAll('#controls .seg button')].find(b => b.textContent === 'Underperforming').click()");
  check(await evaluate("document.querySelectorAll('tr.grp.better').length") === 0, "underperforming slices only");
  await evaluate("(() => { const r = document.querySelector('#controls input[type=range]'); r.value = 5; r.dispatchEvent(new Event('input')); })()");
  check(await evaluate("document.querySelectorAll('tr.slice').length") === 5, "rows slider to 5");
  await evaluate("[...document.querySelectorAll('#controls .seg button')].find(b => b.textContent === '3').click()");
  check(await evaluate("SL.state.get().conj") === 3, "three conditions");
  await shot("02_settings_changed");
  await evaluate("[...document.querySelectorAll('#controls button')].find(b => b.textContent === 'Reset').click()");
  check(await evaluate("document.querySelectorAll('tr.slice').length") === 10 && await evaluate("SL.state.get().target") === "mean", "reset restores the paper's table");

  // 3. click a row: its conversations
  await evaluate("document.querySelector('tr.slice').click()");
  await sleep(900);
  check(await evaluate("document.querySelectorAll('.cv-item').length") === 40, "first row opens its 40 conversations");
  check(await evaluate("document.querySelectorAll('.msgs mark').length") > 0, "evidence highlighted");
  await shot("03_conversation");
  await evaluate("[...document.querySelectorAll('.tabs button')][1].click()");
  check(await evaluate("document.querySelectorAll('table.rubric tbody tr').length") > 3, "rubric tab");
  await evaluate("[...document.querySelectorAll('.tabs button')][2].click()");
  check(await evaluate("document.querySelectorAll('table.labels tr').length") >= 7, "labels tab");
  await evaluate("document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }))");
  await sleep(500);
  check(/Conversation 2 of/.test(await evaluate("document.querySelector('.cv-title').innerText")), "arrow key moves to the next conversation");
  await evaluate("document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))");
  check(await evaluate("document.querySelector('.overlay') === null"), "Esc closes");

  // 4. drill down into Emergency referrals
  await evaluate("[...document.querySelectorAll('.theme-tab')].find(b => b.innerText.startsWith('Emergency')).click()");
  check(await evaluate("SL.state.get().scope") === "emergency_referrals", "Emergency referrals tab");
  check(await evaluate("document.querySelectorAll('tr.slice').length") === 10, "theme table has 10 rows");
  check(/clinical/.test(await evaluate("document.querySelector('tr.slice').innerText")), "worst theme slice: clinical setting");
  check(await evaluate("document.querySelectorAll('.vchip.theme').length") > 0, "theme attributes marked");
  await shot("04_emergency");

  // 5. attributes drawer: a value opens its conversations
  await evaluate("document.getElementById('btn-attrs').click()");
  await evaluate("document.querySelectorAll('.attr-h')[3].click()");
  check(await evaluate("document.querySelectorAll('table.vals tr.click').length") > 1, "attribute values table");
  await shot("05_attributes");
  await evaluate("document.querySelector('table.vals tr.click').click()");
  await sleep(700);
  check(await evaluate("document.querySelectorAll('.cv-item').length") > 0, "attribute value opens conversations");
  await evaluate("document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))");

  // 6. about, export
  await evaluate("document.getElementById('btn-about').click()");
  await shot("06_about");
  await evaluate("document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))");
  await evaluate("[...document.querySelectorAll('#tablecard button')].find(b => b.textContent === 'Export').click()");
  check(/\\begin\{table\*\}/.test(await evaluate("document.querySelector('textarea.code').value")), "LaTeX export");
  await evaluate("document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))");

  // 7. a setting no slice passes: the table says so and offers smaller differences
  await evaluate("SL.state.set({ scope: 'corpus', eff: 0.2 })");
  check(/No slice passes/.test(await evaluate("(document.querySelector('#tablecard .empty') || {}).innerText || ''")), "empty table explains itself");
  await evaluate("document.querySelector('#tablecard .empty button').click()");
  check(Math.abs(await evaluate("SL.state.get().eff") - 0.17) < 1e-9, "button lowers the minimum difference");
  await evaluate("SL.state.reset()");

  // 8. widths
  await evaluate("SL.state.set({ scope: 'corpus' })");
  await shot("08_width_1280", 1280, 900);
  await shot("09_width_1920", 1920, 1080);
  await shot("10_width_820", 820, 1100);
  check(errors.length === 0, `no JavaScript errors${errors.length ? ": " + errors.join(" | ") : ""}`);
}

main().catch((e) => { failures.push(String(e)); console.error(e); }).finally(() => {
  try { ws && ws.close(); } catch {}
  chrome.kill();
  setTimeout(() => { try { fs.rmSync(prof, { recursive: true, force: true }); } catch { /* Chrome still closing */ } }, 500);
  console.log(failures.length ? `${failures.length} check(s) failed` : `all checks passed; screenshots in ${outDir}`);
  setTimeout(() => process.exit(failures.length ? 1 : 0), 700);
});
