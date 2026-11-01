/* The explanation table: one row per slice, both models, the difference. Click a row to read its conversations. */
(function (root) {
  "use strict";
  const SL = root.SL;
  const { h, clear, esc, fmt } = SL.util;
  const { A } = SL.data;
  const dat = SL.data;
  const M = SL.model;

  const who = (t) => (t === "mean" ? "both models" : t === "gpt" ? "GPT-5.5" : "Claude Opus 4.7");

  function title(st, sc) {
    const verb = st.target === "mean" ? "score" : "scores";
    const d = st.dir === "worse" ? "worse than" : st.dir === "better" ? "better than" : "worse or better than";
    return `Where ${who(st.target)} ${verb} ${d} ${sc.theme ? "the theme average" : "their theme average"}`;
  }

  function conds(r) {
    return h("div", { class: "conds" }, r.conds.map(([c, v], i) => [
      i ? h("span", { class: "and" }, "and") : null,
      h("span", { class: "vchip" + (A[c].group === "theme" ? " theme" : ""), "data-tip": esc(A[c].question) },
        h("span", { class: "an" }, A[c].name), h("b", null, dat.label(c, v)))]));
  }

  function mbar(r, model, maxPct, sc) {
    const v = r.pct[model];
    const w = Math.min(50, (Math.abs(v) / maxPct) * 50);
    const style = v < 0 ? { right: "50%", width: w + "%" } : { left: "50%", width: w + "%" };
    const tip = `<b>${model === "gpt" ? "GPT-5.5" : "Claude Opus 4.7"}</b>: average score ${fmt.score(r.abs[model])} in this slice ` +
      `vs ${fmt.score(r.absScope[model])} in ${esc(sc.short)}`;
    return h("div", { class: "mbar", "data-tip": tip },
      h("div", { class: "trk" }, h("span", { class: `fill ${model}`, style })),
      h("span", { class: "v num" }, fmt.pct(v)));
  }

  function row(r, st, res, sc) {
    return h("tr", { class: "slice", onclick: () => SL.views.conversations.open(sc, r.conds) },
      h("td", null, conds(r)),
      h("td", { class: "r num" }, fmt.int(r.n)),
      h("td", null, mbar(r, "gpt", res.maxPct, sc)),
      h("td", null, mbar(r, "claude", res.maxPct, sc)),
      h("td", { class: "r" }, h("span", { class: "diff " + (r.devT < 0 ? "neg" : "pos") }, fmt.pct(r.pctT))),
      h("td", { class: "r" }, h("span", { class: "read" }, "Read →")));
  }

  function render(st, res) {
    const sc = res.scope;
    const card = clear(document.getElementById("tablecard"));
    card.append(h("div", { class: "card-h" },
      h("h2", { class: "card-title" }, title(st, sc)),
      h("button", { class: "btn small", onclick: () => SL.views.exportView.open(), title: "LaTeX table or CSV" }, "Export")));

    if (!res.rows.length) {
      const t = sc.theme ? dat.themeBy[sc.theme] : null;
      const low = t && t.r2 !== null && t.r2 < 0.05;
      card.append(h("div", { class: "empty" },
        h("div", { style: { fontWeight: 600, color: "var(--ink-2)", marginBottom: "6px" } }, "No slice passes these settings."),
        h("div", { style: { maxWidth: "560px", margin: "0 auto 12px" } }, low
          ? `In ${t.name} the text of the conversations explains almost none of the score differences, so any slice here is small.`
          : "Lower the minimum difference or the minimum number of conversations."),
        st.eff > 0.03 ? h("button", { class: "btn small", onclick: () => SL.state.set({ eff: Math.max(0.03, Math.round((st.eff - 0.03) * 100) / 100) }) },
          `Show smaller differences (${Math.max(3, Math.round(st.eff * 100) - 3)} points)`) : null));
      return;
    }

    const all = M.stats(sc, Int32Array.from({ length: sc.n }, (_, i) => i), st);
    const ncol = 6;
    const body = h("tbody", null,
      h("tr", { class: "base" },
        h("td", null, `All ${fmt.int(sc.n)} conversations`),
        h("td", { class: "r num" }, fmt.int(sc.n)),
        h("td", { class: "num" }, `average ${fmt.score(all.abs.gpt)}`),
        h("td", { class: "num" }, `average ${fmt.score(all.abs.claude)}`),
        h("td", { class: "r faint" }, "—"), h("td")));
    if (res.worse.length) {
      body.append(h("tr", { class: "grp worse" }, h("td", { colspan: ncol }, "▼ Underperforming")));
      res.worse.forEach((r) => body.append(row(r, st, res, sc)));
    }
    if (res.better.length) {
      body.append(h("tr", { class: "grp better" }, h("td", { colspan: ncol }, "▲ Overperforming")));
      res.better.forEach((r) => body.append(row(r, st, res, sc)));
    }
    card.append(h("table", { class: "et" },
      h("thead", null, h("tr", null,
        h("th", null, "Slice"),
        h("th", { class: "r" }, "Conversations"),
        h("th", null, h("span", { class: "lm" }, h("i", { class: "dot gpt" }), "GPT-5.5")),
        h("th", null, h("span", { class: "lm" }, h("i", { class: "dot claude" }), "Claude Opus 4.7")),
        h("th", { class: "r", "data-tip": `Difference of ${st.target === "mean" ? "the average of both models' scores" : who(st.target) + "'s score"} from the average, as a share of the average score` },
          "Difference"),
        h("th"))),
      body));
    const hasTheme = res.rows.some((r) => r.conds.some(([c]) => A[c].group === "theme"));
    if (hasTheme) card.append(h("div", { class: "table-foot" }, h("span", { class: "legend-theme" }, h("i"), "attribute discovered inside this theme")));
  }

  SL.views = SL.views || {};
  SL.views.table = { render };
})(window);
