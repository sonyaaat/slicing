# Prompt diffs, version `uc5-v1-theme` (Sliceability v5, theme run)

The v5 prompts (`uc5-v1`) for a run inside one HealthBench theme. P1, P4 and P5 are
byte-identical to `uc5-v1` and keep its cache tag (`prompts.cache_versions` in
`run_config_theme.json`; `load_prompt` checks the claim byte for byte). P2 and P3 drop the
statements that the messages come from several topic areas, which are false inside one theme.
Nothing else changes.

## P2 (contrastive induction, 3b)
- removed "The messages come from several different topic areas."
- "The attribute must make sense for every message shown, whatever its topic area." ->
  "The attribute must make sense for every message shown."
- "from at least 2 different messages that look like they come from different topic areas" ->
  "from at least 2 different messages"

## P3 (critique, 3c)
- removed "The messages come from several different topic areas."
- breadth: "does the attribute make sense for the messages of every topic area represented in
  the observations? (5 = all, 1 = one area only)" -> "does the attribute make sense for every
  message in the observations? (5 = all, 1 = only a few)"

The partition description slot of P2 is the theme's own sentence from the HealthBench paper,
as in run 4 (`partition_description` in the config).
