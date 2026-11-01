"""P5 annotation of one (prompt, attribute) pair. Used unchanged by steps 3d, 5 and 6.

One attribute per call (the spec rejects batching). The order of the attribute's values
is shuffled per call by a seeded RNG keyed on (seed, prompt_id, attribute name), so it
differs between calls but is identical on a rerun - which is what lets the cache work.
The reliability recheck in step 5 passes a different seed, which changes both this
shuffle and the API `seed` parameter.

Outcome of a call is one record. Model faults are never folded into a real value:
  * a value outside {declared values, other, unknown, not_applicable} after
    normalisation is retried; if it persists the record gets value = "parse_error";
  * the gate is authoritative: gate_answer "no" -> not_applicable;
  * inconsistencies that are kept as returned are flagged, not hidden.
"""

from __future__ import annotations

import hashlib
import random
from typing import Any

from common import NA, OTHER, PARSE_ERROR, UNKNOWN, Run, load_prompt, norm_value, render
from llm_client import LLM, LLMError


def gate_line(gate: str | None) -> str | None:
    if not gate or norm_value(gate) == "all":
        return None
    g = gate.strip()
    if g[-1] not in ".?!":
        g += "."
    return f'First decide: {g} If the answer is no, return "not_applicable".'


def shuffled_values(values: list[str], seed: int, pid: str, attr_name: str) -> list[str]:
    h = hashlib.sha256(f"{seed}|{pid}|{attr_name}".encode()).hexdigest()
    rng = random.Random(int(h[:16], 16))
    vals = list(values)
    rng.shuffle(vals)
    return vals


def build_prompt(template: str, attr: dict, user_text: str, seed: int, pid: str) -> str:
    vals = shuffled_values(attr["values"], seed, pid, attr["name"])
    gl = gate_line(attr.get("gate"))
    t = template
    if gl is None:
        t = t.replace("<gate_line>\n", "")
        slots = {}
    else:
        slots = {"gate_line": gl}
    return render(t, question=attr["question"],
                  values=", ".join(f'"{v}"' for v in vals),
                  user_text=user_text, **slots)


def _validator(attr: dict):
    allowed = {norm_value(v): v for v in attr["values"]}
    for sv in (OTHER, UNKNOWN, NA):
        allowed.setdefault(norm_value(sv), sv)

    def check(obj: Any) -> dict:
        if not isinstance(obj, dict) or "value" not in obj:
            raise ValueError("reply is not an object with a 'value' key")
        # P5 says: gate answer no -> return not_applicable. The model often does exactly
        # that in gate_answer and leaves value null; that reply is not_applicable, not a
        # parse error. (Found in the run on 2026-10-15: 70 rejections, all on the one
        # gated attribute.)
        if norm_value(obj.get("value")) in ("", "none", "null") \
                and norm_value(obj.get("gate_answer")) == "no":
            return {**obj, "_value": NA, "_null_value_with_gate_no": True}
        nv = norm_value(obj.get("value"))
        if nv not in allowed:
            # A label that lists alternatives ("a, b, or c") is sometimes answered with one
            # alternative ("b"). Accepted only if it is a listed alternative of exactly one
            # label. Added 2026-10-15 after such replies were found in step 5.
            hits = [lab for lab in attr["values"] if nv and nv in _parts(lab)]
            if len(hits) == 1:
                return {**obj, "_value": hits[0], "_partial_label_match": True}
            raise ValueError(f"value {str(obj.get('value'))[:80]!r} not in allowed set")
        return {**obj, "_value": allowed[nv]}
    return check


def _parts(label: str) -> set[str]:
    """Listed alternatives of a label: 'want, would-like, or requesting statement' ->
    {'want', 'would like', 'requesting statement'} (normalised)."""
    import re
    raw = re.split(r",|/|\bor\b", str(label))
    return {norm_value(p) for p in raw if len(norm_value(p)) >= 3}


def annotate_one(llm: LLM, run: Run, attr: dict, pid: str, user_text: str, *, seed: int,
                 step: str) -> dict:
    """attr needs name, question, gate, values (list of labels, without 'other')."""
    template, version = load_prompt(run, "P5")
    prompt = build_prompt(template, attr, user_text, seed, pid)
    gated = gate_line(attr.get("gate")) is not None
    rec = {"prompt_id": pid, "attribute": attr["name"], "seed": seed, "flags": ""}
    try:
        obj = llm.complete_json(prompt, step=step, prompt_version=version,
                                item=f"{pid}|{attr['name']}", seed=seed,
                                validator=_validator(attr))
    except LLMError as e:
        rec.update(gate_answer=None, value=PARSE_ERROR, value_raw=None, evidence_span=None,
                   unknown_reason=None, flags="parse_error", error=str(e)[:300])
        return rec

    flags = ["null_value_with_gate_no"] if obj.get("_null_value_with_gate_no") else []
    if obj.get("_partial_label_match"):
        flags.append("partial_label_match")
    ga = obj.get("gate_answer")
    ga = None if ga is None else norm_value(ga)
    value = obj["_value"]
    if gated:
        if ga == "no":
            if value != NA:
                flags.append("gate_no_overrides_value")
            value = NA
        elif ga == "yes" and value == NA:
            flags.append("gate_yes_but_na")
        elif ga not in ("yes", "no"):
            flags.append("gate_answer_missing")
    else:
        if value == NA:
            flags.append("na_without_gate")
        ga = None
    ur = obj.get("unknown_reason")
    if value == UNKNOWN and not (ur and str(ur).strip()):
        flags.append("unknown_without_reason")
    rec.update(gate_answer=ga, value=value, value_raw=obj.get("value"),
               evidence_span=obj.get("evidence_span") if value not in (UNKNOWN, NA) else
               (obj.get("evidence_span") or ""),
               unknown_reason=ur if value == UNKNOWN else None,
               flags="|".join(flags), error=None)
    return rec
