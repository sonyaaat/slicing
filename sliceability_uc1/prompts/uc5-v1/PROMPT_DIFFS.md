# Prompt diffs, version `uc5-v1` (Sliceability v5, corpus run 1)

Source: spec "Sliceability v5: універсальні атрибути на всьому корпусі", appendix. All five
prompts are tagged `uc5-v1` in the cache key, including P1 whose text did not change, so no
reply from runs 1-4 is reused.

## P1 (notes, 3a)
Byte-identical to `uc1-v4` (spec: "промпт P1 без змін").

## P2 (contrastive induction, 3b)
The spec's v5 P2 verbatim, with three slots filled:
- `<one sentence about the whole benchmark>` -> the first sentence of the HealthBench abstract
  (arXiv:2505.08775), checked against https://arxiv.org/abs/2505.08775 on 2026-10-16.
- `<from round 2: === ALREADY PROPOSED === block ...>` -> the run-2..4 block, unchanged:
  `=== ALREADY PROPOSED ===`, one `- <name>: <question>` line per attribute proposed in earlier
  rounds, then "Propose attributes that are not in the list above and are not rewordings of
  them. If you cannot find 5 new ones, return fewer." Empty in round 1.
- data lines `<alias>: <facts joined by ' | '>`, as in runs 2-4.

## P3 (critique, 3c)
The `uc1-v4` P3 with the two v5 score lines (breadth, factor) added verbatim to the score list
and to the JSON schema. Other edits, all following from v5 having no gates:
- "for the prompts below" -> "for the messages below"; added "The messages come from several
  different topic areas." (the breadth score refers to topic areas; without this sentence the
  critic has no reason to know there are several).
- removed the gate sentence and the `"gate"` field from the missing-attribute schema, and the
  `"hypothesis"` field (v5 P2 does not ask for one).
- contrast sentence: "Group LOW: messages where two different assistants later answered
  poorly. HIGH: answered well. MID: in between. You never see the answers."

## P4 (merge, 4)
The `uc1-v4` P4 with:
- "Keep gates." removed (no gates in v5).
- "Each value label is at most 5 words ... Reuse one member's label verbatim whenever one
  fits." and "Rewrite each value label so a non-expert ... Keep the question unchanged."
  replaced by the v5 relabel paragraph, verbatim.
- An explicit JSON schema (`old_label` / `new_label` / `folded` / `merged_from`) instead of
  "the same schema as the candidates", because the candidates' schema has no old/new fields.
The verbatim-copy rule is also enforced in code: a label without a comma or "or" is kept as
given even if the model rewrote it (logged in `candidates_merged.json -> label_map`).

## P5 (annotation, 3d / 5 / 6)
The `uc1-v4` P5 with:
- the sentence "If the prompt gives no basis to decide, return "unknown" and say in one
  sentence what is missing." replaced by the v5 four-way rule, verbatim;
- `<gate_line>` and `"gate_answer"` removed (no gates in v5).
Value labels that mean "not stated" (e.g. "age not stated") are not listed in `<values>`: they
are represented by the `not_stated` output, and an annotator reply with either form is stored
as `not_stated`. Without this the annotator would choose between two spellings of the same
answer at random, which would show up as unreliability.
