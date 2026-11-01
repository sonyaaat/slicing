/* The settings bar above the table. Built once and synced on every change, so a slider keeps
 * focus while it is dragged; rebuilt when the scope changes (its slider range differs). */
(function (root) {
  "use strict";
  const SL = root.SL;
  const { h, clear, put } = SL.util;
  let builtFor = null;
  const refs = {};

  function seg(key, label, options) {
    const wrap = h("div", { class: "seg", role: "group", "aria-label": label });
    refs[key] = { type: "seg", btns: options.map(([v, text]) => {
      const b = h("button", { type: "button", onclick: () => SL.state.set({ [key]: v }) }, text);
      b._v = v; wrap.append(b); return b;
    }) };
    return h("div", { class: "tb" }, h("div", { class: "tb-label" }, label), wrap);
  }

  function range(key, label, min, max, step, show, tip) {
    const val = h("span", { class: "val" });
    const inp = h("input", { type: "range", min, max, step, "aria-label": label,
      oninput: (e) => { const v = parseFloat(e.target.value); val.textContent = show(v); SL.state.set({ [key]: v }); } });
    refs[key] = { type: "range", inp, val, show };
    return h("div", { class: "tb", "data-tip": tip }, h("div", { class: "tb-label" }, h("span", null, label), val), inp);
  }

  function build(st) {
    const theme = !!SL.data.scope(st.scope).theme;
    put(clear(document.getElementById("controls")),
      seg("target", "Score of", [["mean", "Both models"], ["gpt", "GPT-5.5"], ["claude", "Claude"]]),
      seg("dir", "Show slices", [["worse", "Underperforming"], ["both", "Both"], ["better", "Overperforming"]]),
      range("k", "Rows", 1, 15, 1, (v) => `${v}`, "How many slices the table shows"),
      theme ? range("sup", "Min. conversations", 5, 80, 1, (v) => `${v}`, "The smallest slice the table may show")
            : range("sup", "Min. conversations", 10, 200, 5, (v) => `${v}`, "The smallest slice the table may show"),
      range("eff", "Min. difference", 0.01, 0.2, 0.01, (v) => `${Math.round(v * 100)} pts`, "The smallest score difference, in points of the 0–100 rubric score"),
      seg("conj", "Conditions", [[1, "1"], [2, "2"], [3, "3"]]),
      h("button", { class: "linkbtn tb-reset", onclick: () => SL.state.reset() }, "Reset"));
    builtFor = st.scope;
  }

  function sync(st) {
    if (builtFor !== st.scope) build(st);
    for (const [key, r] of Object.entries(refs)) {
      if (r.type === "seg") r.btns.forEach((b) => b.classList.toggle("on", b._v === st[key]));
      else if (r.type === "range") { if (document.activeElement !== r.inp) r.inp.value = st[key]; r.val.textContent = r.show(st[key]); }
    }
  }

  SL.views = SL.views || {};
  SL.views.controls = { sync };
})(window);
