/* "How it works": the pipeline with the run's own numbers, and how to read the screen. */
(function (root) {
  "use strict";
  const SL = root.SL;
  const { h, fmt, joinAnd } = SL.util;
  const { D, attrName } = SL.data;
  let R = null;

  /* one pipeline step: number badge, title and text, the count it ends with */
  function step(no, t, d, big, unit, note) {
    return h("li", { class: "pstep" },
      h("div", { class: "pno" }, String(no)),
      h("div", { class: "pbody" }, h("div", { class: "pt" }, t), h("div", { class: "pd" }, d),
        note ? h("div", { class: "pn" }, note) : null),
      h("div", { class: "pk" }, h("div", { class: "big num" }, big), h("div", { class: "u" }, unit)));
  }

  function card(t, ...kids) {
    return h("div", { class: "rcard" }, h("div", { class: "rt" }, t), h("p", null, kids));
  }

  function open() {
    close();
    const p = D.pipeline;
    const m = D.meta;
    const subsetCols = ((m.subset_rule.match(/\{([^}]*)\}/) || [])[1] || "").split(",").map((c) => c.trim()).filter(Boolean);
    const body = h("div", { class: "modal-b about" },
      h("p", { class: "lead" }, `${m.benchmark}. Each conversation has a physician-written rubric; its score is the share of rubric points the answer earned, graded by ${m.judge}. ` +
        "The question is where the two models answer worse or better than usual, described in words a clinician can read."),

      h("div", { class: "eyebrow" }, "Pipeline"),
      h("ol", { class: "pipe" },
        step(1, "Extract facts", `Each conversation in the ${Math.round(p.split * 100)}% discovery split is reduced to a few key facts.`,
          fmt.int(p.notes), "conversations"),
        step(2, "Contrast", `${p.rounds.length} rounds. Each shows the discovery model ${p.per_round} low- and ${p.per_round} high-scoring conversations; it proposes attributes that separate them.`,
          fmt.int(p.proposed), "candidate attributes", `per round: ${p.rounds.join(", ")}`),
        step(3, "Critique, verify, merge", `A critic pass keeps ${p.critique_survivors}. Every cited example is checked; ${p.verified_universal} attributes hold across at least 3 themes. Duplicates are merged.`,
          fmt.int(p.merged), "attributes"),
        step(4, "Curate", "Kept if coverage ≥ 0.7, each value has enough support, reliability ≥ 0.8 and Cramér's V < 0.5.",
          fmt.int(p.curated), `attributes, ${p.used} searched`,
          `The ${p.used} about the situation are searched here; the other ${p.form_excluded.length} describe the form of the request (${joinAnd(p.form_excluded)}).`),
        step(5, "Slice", "Every conversation is annotated with the attributes, then one explanation table is fit per model.",
          fmt.int(m.n_all), "conversations",
          subsetCols.length ? `The table searches the ${fmt.int(m.n)} where at least two of ${joinAnd(subsetCols.map((c) => attrName(c).toLowerCase()))} are stated.` : null)),

      h("div", { class: "eyebrow" }, "Reading the screen"),
      h("div", { class: "rcards" },
        card("Themes", h("i", null, "All themes"), " compares every conversation with the average of its own theme, so a hard theme is not a slice by itself. A theme tab drills down into that theme."),
        card("The table", "Each row is a combination of discovered attribute values. Rows are picked greedily: each explains the most score variation the rows before it leave unexplained. " +
          "Changing a setting reruns the search in your browser. The numbers describe the conversations the slices were found in."),
        card("Conversations", "Click a row to read its conversations: the annotator's evidence is highlighted, both answers are shown, and the physician rubric shows what each model met.")),

      h("div", { class: "eyebrow" }, "Models and cost"),
      h("dl", { class: "kv" },
        h("dt", null, "Discovery and critique"), h("dd", null, h("code", null, p.discovery_model)),
        h("dt", null, "Facts, verification, annotation"), h("dd", null, h("code", null, p.annotation_model), " self-hosted"),
        h("dt", null, "Second annotator, for agreement"), h("dd", null, h("code", null, p.second_annotator)),
        h("dt", null, "Merging duplicates"), h("dd", null, h("code", null, p.embedding_model.replace("BAAI/", "")), " embeddings"),
        h("dt", null, "Rubric judge"), h("dd", null, h("code", null, m.judge)),
        h("dt", null, "Discovery-model cost"), h("dd", null, h("b", { class: "num" }, `$${p.cost_usd.toFixed(2)}`), " for the whole corpus run")),

      h("p", { class: "canary" }, `HealthBench canary ${m.canary}. Example text stays on this machine; there is no text export.`));
    const md = h("div", { class: "modal about-modal", role: "dialog", "aria-label": "How it works" },
      h("div", { class: "sheet-h" }, h("div", { class: "grow" }, h("h3", { class: "card-title" }, "How it works"),
        h("div", { class: "card-sub" }, "From free-text conversations to readable slices, with no hand-written attribute list")),
        h("button", { class: "xbtn", "aria-label": "Close", onclick: close }, "×")), body);
    const ov = h("div", { class: "overlay", onclick: (e) => { if (e.target === ov) close(); } }, md);
    R = ov;
    document.getElementById("overlay-root").append(ov);
    document.addEventListener("keydown", onKey);
  }
  function onKey(e) { if (e.key === "Escape") close(); }
  function close() { if (R) R.remove(); R = null; document.removeEventListener("keydown", onKey); }

  SL.views = SL.views || {};
  SL.views.about = { open, close };
})(window);
