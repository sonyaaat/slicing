/* Scope tabs: all themes, or the drill-down into Emergency referrals (the one theme with its own discovery run). */
(function (root) {
  "use strict";
  const SL = root.SL;
  const { h, clear, fmt, esc } = SL.util;
  const { D } = SL.data;

  function tab(st, key, name, n, tip) {
    const on = st.scope === key;
    return h("button", { class: "theme-tab" + (on ? " active" : ""), "aria-pressed": on ? "true" : "false", "data-tip": tip,
      onclick: () => { if (!on) SL.state.set({ scope: key }, { push: true }); } },
    name, h("span", { class: "n" }, fmt.int(n)));
  }

  function renderScopes(st) {
    const bar = clear(document.getElementById("scopebar"));
    bar.append(tab(st, "corpus", "All themes", D.meta.n,
      `Average score: GPT-5.5 ${fmt.score(D.meta.mean_gpt)}, Claude Opus 4.7 ${fmt.score(D.meta.mean_claude)}.` +
      "<br><span class='m'>Each conversation is compared with the average of its own theme.</span>"));
    const nTheme = D.attributes.filter((a) => a.group === "theme").length;
    for (const t of D.themes.filter((x) => x.theme_attrs)) {
      bar.append(tab(st, t.key, t.short, t.n,
        `<b>${esc(t.name)}</b><br>Average score: GPT-5.5 ${fmt.score(t.mean_gpt)}, Claude Opus 4.7 ${fmt.score(t.mean_claude)}.` +
        (t.theme_attrs ? `<br><span class='m'>Discovery was also run inside this theme: ${nTheme} more attributes.</span>` : "")));
    }
  }

  SL.views = SL.views || {};
  SL.views.header = { renderScopes };
})(window);
