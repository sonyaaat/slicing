# Sliceability v5 pipeline

From the two HealthBench `.eval` logs to attribute definitions, a full annotation, explanation
tables and their held-out confirmation. Run everything from the repository root with the
repository's `.venv`. Everything the pipeline writes stays inside this folder.

## Steps

`code/v5_main.py` runs the steps of one run directory `runs/<ts>/` in this order; a step
recorded as done in `checkpoint.json` is skipped, and a step that failed midway resumes from
the LLM cache.

| Step | Script | Output |
|---|---|---|
| 1, 2 | `v5_data.py` | `corpus_data.csv` (4,027 conversations, scores, theme-centred scores), `split_corpus.csv` (60/40, seed 42) |
| 0 | `v5_step0.py` | `step0_r2.csv`: how much of each target the text explains (bge-m3 + ridge); picks the target |
| 3a–3d | `v5_discovery.py` | notes per discovery conversation, candidate attributes in 5 rounds, critique, evidence check |
| 4 | `v5_merge.py` | merged attributes with plain value labels |
| 5 | `v5_curate.py` | 300-conversation sample annotated three times; coverage, support, reliability, redundancy filters → `attributes_final.json` |
| 6, prereg | `v5_tables.py` | `annotations_full.csv` (all 4,027), explanation tables on the discovery split, `preregistered_rules.json` |
| 8a | `v5_synth.py` | synthetic check: planted groups the table must recover |
| report | `v5_report.py` | `REPORT_corpus_run1.md` |
| 7 | `v5_step7.py` | held-out confirmation on the confirmation split, run explicitly (`--steps 7`), once |

```bash
.venv/bin/python -m sliceability_uc1.run_corpus --run-id <ts> --steps all     # new run or resume
.venv/bin/python -m sliceability_uc1.run_corpus --run-id <ts> --steps 7
.venv/bin/python -m sliceability_uc1.run_corpus --run-id <ts> --config run_config_theme.json --steps all  # theme run
sliceability_uc1/launch_corpus.sh <ts>                                        # detached, keeps the Mac awake
```

After a corpus run, without model calls:

```bash
.venv/bin/python sliceability_uc1/code/v5_subset.py sliceability_uc1/runs/<corpus run>          # subset S2 + its step 7
.venv/bin/python sliceability_uc1/code/v5_full_tables2.py sliceability_uc1/runs/<corpus run> v3 # full-data S2 tables
.venv/bin/python sliceability_uc1/code/v5_theme_overlap.py sliceability_uc1/runs/<theme run>    # theme vs universal attributes
```

`v5_full_tables2.py` versions: `v3` corpus tables (the demo's "All themes" tab), `v4` the same
with up to 3 conditions, `v5` Emergency referrals with the theme run's attributes (the demo's
Emergency referrals tab), `v6` Emergency referrals on the theme attributes only. Versions v2–v4
read the annotations of run 4 (`runs/20261016T235755Z/`), which is kept locally and not
published.

## Files

| Path | What it is |
|---|---|
| `run_config_corpus.json` | master config of the corpus run: every seed, threshold, model and prompt version; copied into a new run directory, which then reads only its copy |
| `run_config_theme.json` | the same pipeline inside one theme (emergency_referrals); reuses the corpus run's data and split |
| `prompts/uc5-v1/`, `prompts/uc5-v1-theme/` | the prompts P1–P5; `PROMPT_DIFFS.md` records every change |
| `code/` | the v5 scripts and the shared modules they import (`common.py`, `llm_client.py`, `annotate.py`, `et.py`, `step1_data.py`, `step3_discovery.py`, `step4_merge.py`, `step5_curate.py`) |
| `runs/20261017T030528Z/` | the corpus run (all themes); `subset_s2/` holds the subset S2 results and the full-data tables `full_tables_v2`–`v6` |
| `runs/20261028T201353Z/` | the theme run inside Emergency referrals |
| `cache/` | LLM response cache (not published) |

Only run files without HealthBench text are published (see `.gitignore`): configs, attribute
definitions and metrics, tables, confirmation results and reports. Annotations, notes, evidence
quotes and the corpus data stay local.
