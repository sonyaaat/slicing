/* Attributes panel: the discovered attributes, one line each, with a switch for the search.
 * Click a line for its values; click a value to read its conversations. */
(function (root) {
  "use strict";
  const SL = root.SL;
  const { h, clear, put, esc, fmt } = SL.util;
  const { D } = SL.data;
  const dat = SL.data;
  let R = null;
  const expanded = new Set();

  function values(a, st) {
    const sc = dat.scope(a.group === "theme" ? "emergency_referrals" : st.scope);
    if (!sc.cols.includes(a.col)) return null;
    const rows = a.values.filter((v) => !v.excluded && !v.absence)
      .map((v) => { const idx = dat.indexOf(sc, [[a.col, v.raw]]); return { v, idx, s: SL.model.stats(sc, idx, st) }; })
      .filter((r) => r.idx.length).sort((x, y) => y.idx.length - x.idx.length);
    const pct = (x) => h("td", { class: "num " + (x < 0 ? "neg" : "pos"), style: { textAlign: "right" } }, fmt.pct(x));
    return h("table", { class: "vals" },
      h("tr", null, h("th", null, "Value"), h("th", { style: { textAlign: "right" } }, "Conversations"),
        h("th", { style: { textAlign: "right" } }, "GPT-5.5"), h("th", { style: { textAlign: "right" } }, "Claude")),
      rows.map(({ v, idx, s }) => h("tr", { class: "click", title: "Read these conversations",
        onclick: () => { close(); SL.views.conversations.open(sc, [[a.col, v.raw]]); } },
        h("td", null, v.label),
        h("td", { class: "num", style: { textAlign: "right" } }, fmt.int(idx.length)),
        pct(s.pct.gpt), pct(s.pct.claude))));
  }

  function line(a, st) {
    const off = st.off.includes(a.col);
    const open = expanded.has(a.col);
    const tog = h("label", { class: "toggle", "data-tip": "Use in the search", onclick: (e) => e.stopPropagation() },
      h("input", { type: "checkbox", checked: off ? null : true, onchange: (e) => {
        const cur = SL.state.get().off;
        SL.state.set({ off: e.target.checked ? cur.filter((x) => x !== a.col) : cur.concat([a.col]) });
        render();
      } }), h("span"));
    return h("div", { class: "attr" + (off ? " off" : "") + (open ? " open" : "") },
      h("div", { class: "attr-h", onclick: () => { open ? expanded.delete(a.col) : expanded.add(a.col); render(); } },
        h("span", { class: "attr-caret" }, open ? "▾" : "▸"),
        h("span", { class: "attr-name" }, a.name),
        h("span", { class: "attr-vals" }, a.values.filter((v) => !v.excluded && !v.absence).map((v) => v.label).join(" · ")),
        tog),
      open ? h("div", { class: "attr-b" },
        h("div", { class: "attr-q" }, a.question, a.metrics ? h("span", { class: "faint" }, ` · reliability ${a.metrics.reliability.toFixed(2)}`) : null),
        values(a, st)) : null);
  }

  function render() {
    if (!R) return;
    const st = SL.state.get();
    const uni = D.attributes.filter((a) => a.group === "universal");
    const th = D.attributes.filter((a) => a.group === "theme");
    put(clear(R.body),
      h("div", { class: "eyebrow attr-sec" }, `All themes · ${uni.length}`),
      uni.map((a) => line(a, st)),
      h("div", { class: "eyebrow attr-sec" }, `Emergency referrals · ${th.length}`),
      th.map((a) => line(a, st)));
  }

  function open(focus) {
    close();
    const body = h("div", { class: "drawer-b" });
    const dr = h("div", { class: "drawer", role: "dialog", "aria-label": "Discovered attributes" },
      h("div", { class: "sheet-h" }, h("div", { class: "grow" }, h("h3", { class: "card-title" }, "Discovered attributes")),
        h("button", { class: "xbtn", "aria-label": "Close", onclick: close }, "×")),
      body);
    const ov = h("div", { class: "overlay", style: { justifyContent: "flex-end" }, onclick: (e) => { if (e.target === ov) close(); } }, dr);
    R = { root: ov, body };
    if (focus) expanded.add(focus);
    document.getElementById("overlay-root").append(ov);
    document.addEventListener("keydown", onKey);
    render();
  }
  function onKey(e) { if (e.key === "Escape") close(); }
  function close() {
    if (R) R.root.remove();
    R = null;
    document.removeEventListener("keydown", onKey);
  }

  SL.views = SL.views || {};
  SL.views.attributes = { open, close };
})(window);
