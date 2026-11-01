/* App state, kept in the URL hash so every view can be linked and reloaded. */
(function (root) {
  "use strict";
  const SL = (root.SL = root.SL || {});

  const DEF = { scope: "corpus", target: "mean", dir: "both", k: 10, sup: 40, conj: 2, eff: 0.05, off: [] };
  const KEYS = { scope: "s", target: "t", dir: "d", k: "k", sup: "m", conj: "c", eff: "e", off: "off" };
  let st = { ...DEF };
  const listeners = [];

  function scopeDefaults(scope) {
    const d = SL.data.scope(scope).defaults;
    return { k: d.k, sup: d.sup, eff: d.eff, conj: d.conj };
  }

  function parse(hash) {
    const p = new URLSearchParams((hash || "").replace(/^#/, ""));
    const s = { ...DEF };
    const scope = p.get("s");
    if (scope && (scope === "corpus" || (SL.data.themeBy[scope] && SL.data.themeBy[scope].theme_attrs))) s.scope = scope;
    Object.assign(s, scopeDefaults(s.scope));
    if (["mean", "gpt", "claude"].includes(p.get("t"))) s.target = p.get("t");
    if (["both", "worse", "better"].includes(p.get("d"))) s.dir = p.get("d");
    const int = (k, lo, hi) => { const v = parseInt(p.get(k), 10); return isNaN(v) ? null : Math.max(lo, Math.min(hi, v)); };
    const k = int("k", 1, 20); if (k !== null) s.k = k;
    const m = int("m", 5, 500); if (m !== null) s.sup = m;
    const c = int("c", 1, 3); if (c !== null) s.conj = c;
    const e = parseFloat(p.get("e")); if (!isNaN(e)) s.eff = Math.max(0, Math.min(0.5, e));
    if (p.get("off")) s.off = p.get("off").split(",").filter((x) => SL.data.A[x]);
    return s;
  }

  function serialize(s) {
    const p = new URLSearchParams();
    for (const [k, short] of Object.entries(KEYS)) {
      if (k === "off") { if (s.off.length) p.set(short, s.off.join(",")); continue; }
      p.set(short, String(s[k]));
    }
    return "#" + p.toString();
  }

  function get() { return st; }

  /* set(patch, {push}) - merges, writes the hash, notifies */
  function set(patch, opts = {}) {
    const prev = st;
    let next = { ...st, ...patch };
    if (patch.scope && patch.scope !== prev.scope) next = { ...st, ...scopeDefaults(patch.scope), ...patch };  // explicit values win over the scope's defaults
    st = next;
    const h = serialize(st);
    if (h !== location.hash) {
      if (opts.push) history.pushState(null, "", h); else history.replaceState(null, "", h);
    }
    listeners.forEach((fn) => fn(st, prev));
  }

  function reset() { set({ ...DEF, scope: st.scope, ...scopeDefaults(st.scope), off: [] }); }

  function init() {
    st = parse(location.hash);
    window.addEventListener("popstate", () => { const prev = st; st = parse(location.hash); listeners.forEach((fn) => fn(st, prev)); });
  }

  function onChange(fn) { listeners.push(fn); }

  SL.state = { get, set, reset, init, onChange, parse, serialize, DEF };
})(window);
