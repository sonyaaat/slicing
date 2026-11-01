"""P5 (v5) annotation of one (prompt, attribute) pair. Used by 3d, 5 and 6.

Outputs a record whose `value` is one of:
  a listed value label, "other", "none of these" (if listed),
  "not_stated", "not_applicable", "unknown", or "parse_error" (model fault after retries).

Absence labels. A value label that means "not stated" ("age not stated", "no time given")
is the same answer as the P5 output `not_stated`. Such labels are not listed in the prompt
and every reply of either form is stored as `not_stated` (see PROMPT_DIFFS.md, P5).

The value order is shuffled per call by a seeded RNG keyed on (seed, prompt_id, attribute
name), as in runs 1-4 (annotate.shuffled_values), so a rerun renders the same prompt.
"""

from __future__ import annotations

import re
from typing import Any

from annotate import _parts, shuffled_values
from common import NA, OTHER, PARSE_ERROR, UNKNOWN, Run, load_prompt, norm_value, render
from llm_client import LLMError

NOT_STATED = "not_stated"
NONE_LABEL = "none of these"
SPECIAL_V5 = (NOT_STATED, NA, UNKNOWN)

_ABSENCE = re.compile(
    # "given" / "provided" are left out on purpose: "medicine not given" is a fact about
    # the situation, not an absence of information.
    r"\bnot (stated|mentioned|specified|said|indicated|described)\b"
    r"|\bunspecified\b|\bunstated\b|\bnone (stated|mentioned)\b"
    r"|^no\b.{0,30}\b(stated|mentioned|specified)$", re.I)


def is_absence_label(label: str) -> bool:
    n = norm_value(label)
    return n in ("not stated", "none stated", "unstated") or bool(_ABSENCE.search(n))


def canonical(value: str) -> str:
    """Comparison form of a stored or claimed value: absence labels -> not_stated."""
    if value in (NOT_STATED, NA, UNKNOWN, OTHER, PARSE_ERROR):
        return value
    if is_absence_label(value):
        return NOT_STATED
    return norm_value(value)


def listed_values(values: list[str]) -> list[str]:
    """The labels shown in the prompt: every value except absence labels."""
    return [v for v in values if not is_absence_label(v)]


def build_prompt(template: str, attr: dict, user_text: str, seed: int, pid: str) -> str:
    vals = shuffled_values(listed_values(attr["values"]), seed, pid, attr["name"])
    return render(template, question=attr["question"],
                  values=", ".join(f'"{v}"' for v in vals), user_text=user_text)


def _validator(attr: dict):
    shown = listed_values(attr["values"])
    allowed = {norm_value(v): v for v in shown}
    allowed.setdefault(norm_value(OTHER), OTHER)
    for sv in SPECIAL_V5:
        allowed.setdefault(norm_value(sv), sv)        # "not stated" / "not applicable" too

    def check(obj: Any) -> dict:
        if not isinstance(obj, dict) or "value" not in obj:
            raise ValueError("reply is not an object with a 'value' key")
        raw = obj.get("value")
        nv = norm_value(raw)
        if nv in allowed:
            return {**obj, "_value": allowed[nv]}
        if raw is not None and is_absence_label(str(raw)):
            return {**obj, "_value": NOT_STATED, "_absence_label_reply": True}
        hits = [lab for lab in shown if nv and nv in _parts(lab)]
        if len(hits) == 1:
            return {**obj, "_value": hits[0], "_partial_label_match": True}
        raise ValueError(f"value {str(raw)[:80]!r} not in allowed set")
    return check


def annotate_one(llm, run: Run, attr: dict, pid: str, user_text: str, *, seed: int,
                 step: str) -> dict:
    """attr: name, question, values (labels, may include absence labels and 'none of these')."""
    template, version = load_prompt(run, "P5")
    prompt = build_prompt(template, attr, user_text, seed, pid)
    rec = {"prompt_id": pid, "attribute": attr["name"], "seed": seed, "model": llm.model,
           "flags": ""}
    try:
        obj = llm.complete_json(prompt, step=step, prompt_version=version,
                                item=f"{pid}|{attr['name']}", seed=seed,
                                validator=_validator(attr))
    except LLMError as e:
        rec.update(value=PARSE_ERROR, value_raw=None, evidence_span=None, unknown_reason=None,
                   flags="parse_error", error=str(e)[:300], _failed=True)
        return rec
    flags = []
    if obj.get("_partial_label_match"):
        flags.append("partial_label_match")
    if obj.get("_absence_label_reply"):
        flags.append("absence_label_reply")
    value = obj["_value"]
    ur = obj.get("unknown_reason")
    if value == UNKNOWN and not (ur and str(ur).strip()):
        flags.append("unknown_without_reason")
    span = obj.get("evidence_span")
    rec.update(value=value, value_raw=None if obj.get("value") is None else str(obj.get("value")),
               evidence_span=None if span is None else str(span),
               unknown_reason=str(ur) if (value == UNKNOWN and ur) else None,
               flags="|".join(flags), error=None)
    return rec
