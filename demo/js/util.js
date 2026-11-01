/* Small DOM, formatting, markdown and highlighting helpers. */
(function (root) {
  "use strict";
  const SL = (root.SL = root.SL || {});
  const MINUS = "−";

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  /* h("div", {class: "x", onclick: fn}, child, "text", [more]) */
  function h(tag, props, ...kids) {
    const el = document.createElement(tag);
    if (props) {
      for (const [k, v] of Object.entries(props)) {
        if (v == null || v === false) continue;
        if (k === "class") el.className = v;
        else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
        else if (k === "html") el.innerHTML = v;
        else if (k === "dataset") Object.assign(el.dataset, v);
        else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
        else el.setAttribute(k, v === true ? "" : v);
      }
    }
    for (const kid of kids.flat(Infinity)) {
      if (kid == null || kid === false) continue;
      el.appendChild(kid instanceof Node ? kid : document.createTextNode(String(kid)));
    }
    return el;
  }

  function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }

  /* append children like h() does: arrays flattened, null / false skipped */
  function put(el, ...kids) {
    for (const kid of kids.flat(Infinity)) {
      if (kid == null || kid === false) continue;
      el.appendChild(kid instanceof Node ? kid : document.createTextNode(String(kid)));
    }
    return el;
  }

  function signed(x, d) {
    const r = Number(x.toFixed(d));
    if (r === 0) return (0).toFixed(d);
    return (r < 0 ? MINUS : "+") + Math.abs(r).toFixed(d);
  }
  const fmt = {
    int: (n) => Math.round(n).toLocaleString("en-US"),
    pts: (x, d = 1) => signed(100 * x, d),                 // score difference in points
    pct: (x) => signed(100 * x, 0) + "%",                  // share of the mean score
    score: (x) => (x == null || isNaN(x) ? "–" : `${Math.round(100 * x)}/100`),  // rubric score out of 100
    share: (x) => (100 * x < 1 ? (100 * x).toFixed(1) : Math.round(100 * x).toString()) + "%",
    signed,
  };

  function ordinal(n) {
    const s = ["th", "st", "nd", "rd"], v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]);
  }

  function joinAnd(parts) {
    if (parts.length <= 1) return parts.join("");
    return parts.slice(0, -1).join(", ") + " and " + parts[parts.length - 1];
  }

  function cap(s) { return s ? s[0].toUpperCase() + s.slice(1) : s; }

  /* Mini markdown for model answers: paragraphs, headings, bullet and numbered lists, tables,
   * bold, italics, inline code. Input is escaped first, so the output is safe HTML. */
  function md(text) {
    const lines = String(text || "").replace(/\r\n/g, "\n").split("\n");
    let html = "", list = null, para = [], table = [];
    const inline = (s) => esc(s)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/__([^_]+)__/g, "<strong>$1</strong>")
      .replace(/(^|[\s(])\*([^*\s][^*]*)\*(?=[\s).,;:!?]|$)/g, "$1<em>$2</em>");
    const flushPara = () => { if (para.length) { html += "<p>" + para.map(inline).join("<br>") + "</p>"; para = []; } };
    const closeList = () => { if (list) { html += `</${list}>`; list = null; } };
    const flushTable = () => {
      if (!table.length) return;
      const rows = table.filter((r) => !/^\s*\|?\s*:?-{2,}/.test(r)).map((r) =>
        r.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim()));
      html += "<table class='md-table'>" + rows.map((r, i) =>
        "<tr>" + r.map((c) => (i === 0 ? `<th>${inline(c)}</th>` : `<td>${inline(c)}</td>`)).join("") + "</tr>").join("") + "</table>";
      table = [];
    };
    for (const raw of lines) {
      const line = raw.replace(/\s+$/, "");
      let m;
      if (/^\s*\|/.test(line)) { flushPara(); closeList(); table.push(line); continue; }
      flushTable();
      if (!line.trim()) { flushPara(); closeList(); continue; }
      if ((m = line.match(/^\s*#{1,6}\s+(.*)$/))) { flushPara(); closeList(); html += `<h5>${inline(m[1])}</h5>`; continue; }
      if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) { flushPara(); closeList(); html += "<hr>"; continue; }
      if ((m = line.match(/^\s*[-*•]\s+(.*)$/))) {
        flushPara(); if (list !== "ul") { closeList(); html += "<ul>"; list = "ul"; }
        html += `<li>${inline(m[1])}</li>`; continue;
      }
      if ((m = line.match(/^\s*\d+[.)]\s+(.*)$/))) {
        flushPara(); if (list !== "ol") { closeList(); html += "<ol>"; list = "ol"; }
        html += `<li>${inline(m[1])}</li>`; continue;
      }
      closeList();
      para.push(line);
    }
    flushTable(); flushPara(); closeList();
    return html;
  }

  /* Highlight evidence spans in text. marks: [{span, cls}]. Matching ignores case and
   * whitespace differences. Returns {html, found: Set of mark indices}. */
  function highlight(text, marks) {
    const ranges = [];
    const found = new Set();
    marks.forEach((mk, i) => {
      if (!mk.span) return;
      const pat = mk.span.trim().replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\s+/g, "\\s+");
      if (!pat) return;
      const m = new RegExp(pat, "i").exec(text);
      if (m) { ranges.push([m.index, m.index + m[0].length, mk.cls, i]); found.add(i); }
    });
    ranges.sort((a, b) => a[0] - b[0] || b[1] - a[1]);
    let html = "", pos = 0;
    for (const [s, e, cls, i] of ranges) {
      if (s < pos) continue;
      html += esc(text.slice(pos, s)) + `<mark class="${cls}" data-mark="${i}">` + esc(text.slice(s, e)) + "</mark>";
      pos = e;
    }
    html += esc(text.slice(pos));
    return { html: html.replace(/\n/g, "<br>"), found };
  }

  function download(name, text, type) {
    const blob = new Blob([text], { type: type || "text/plain" });
    const a = h("a", { href: URL.createObjectURL(blob), download: name });
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  async function copyText(text) {
    try { await navigator.clipboard.writeText(text); return true; } catch (e) {
      const ta = h("textarea", { style: { position: "fixed", opacity: "0" } }); ta.value = text;
      document.body.appendChild(ta); ta.select();
      let ok = false; try { ok = document.execCommand("copy"); } catch (e2) { ok = false; }
      ta.remove(); return ok;
    }
  }

  /* Shared floating tooltip. */
  const tip = {
    el: null,
    show(html, x, y) {
      if (!this.el) this.el = document.getElementById("tooltip");
      this.el.innerHTML = html; this.el.hidden = false;
      const r = this.el.getBoundingClientRect();
      let left = x + 14, top = y + 14;
      if (left + r.width > window.innerWidth - 8) left = x - r.width - 14;
      if (top + r.height > window.innerHeight - 8) top = y - r.height - 14;
      this.el.style.left = Math.max(8, left) + "px"; this.el.style.top = Math.max(8, top) + "px";
    },
    hide() { if (this.el) this.el.hidden = true; },
  };
  /* elements with data-tip="html" show it on hover */
  document.addEventListener("mouseover", (e) => {
    const t = e.target.closest && e.target.closest("[data-tip]");
    if (t) tip.show(t.getAttribute("data-tip"), e.clientX, e.clientY);
  });
  document.addEventListener("mousemove", (e) => {
    const t = e.target.closest && e.target.closest("[data-tip]");
    if (t && tip.el && !tip.el.hidden) tip.show(t.getAttribute("data-tip"), e.clientX, e.clientY);
  });
  document.addEventListener("mouseout", (e) => {
    const t = e.target.closest && e.target.closest("[data-tip]");
    if (t && !(e.relatedTarget && t.contains(e.relatedTarget))) tip.hide();
  });

  SL.util = { esc, h, clear, put, fmt, ordinal, joinAnd, cap, md, highlight, download, copyText, tip, MINUS };
})(window);
