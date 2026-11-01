/* Wires state, search and views. Every state change reruns the (cached) search and redraws. */
(function (root) {
  "use strict";
  if (!root.SLICE_DATA) return;
  const SL = root.SL;
  SL.APP_NAME = "Sliceability";           // the paper's [SystemName]: change it here and in index.html
  document.getElementById("app-name").textContent = SL.APP_NAME;

  function update(st) {
    const res = SL.model.search(st);
    SL.views.header.renderScopes(st);
    SL.views.controls.sync(st);
    SL.views.table.render(st, res);
  }

  SL.state.init();
  SL.state.onChange(update);
  document.getElementById("btn-attrs").addEventListener("click", () => SL.views.attributes.open());
  document.getElementById("btn-about").addEventListener("click", () => SL.views.about.open());
  update(SL.state.get());
  SL.app = { update };
})(window);
