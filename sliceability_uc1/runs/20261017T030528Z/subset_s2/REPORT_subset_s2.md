# Sliceability v5 — corpus run 1, subset run S2

Run `20261017T030528Z`, outputs in `subset_s2/`. No model call. Started 2026-10-17T16:39:19+00:00 (UTC); rules registered at 2026-10-17T16:39:40+00:00; confirmation part read at 2026-10-17T16:39:40+00:00.

**This is the second read of these confirmation items.** Step 7 of the main run read the full confirmation split at 2026-10-17T14:02:39+00:00. The subset rule, the attribute set and all thresholds below were fixed before this run started, but the items themselves are no longer unseen, and the confirmation here is weaker than a first read.

## 1. Subset definition and what it excludes

**S2** = at least 2 of {episode_timing, symptom_course, possible_trigger} hold a value not in {not_applicable, unknown, parse_error}. n = 3077 of 4,027 (76.4%); existing split restricted to S2: discovery 1850, confirmation 1227.

Attributes: patient_age, episode_timing, possible_trigger, care_setting, symptom_course, intervention_type, evidence_basis, theme. Excluded form attributes: request_structure, output_constraints, source_material. Values never in a rule: unknown, not_applicable, parse_error, other, none of these; `not_stated` is allowed.

**Theme shift** (items in / out of S2 per theme):

| theme | out_S2 | in_S2 | total | share_in |
|---|---|---|---|---|
| communication | 267 | 518 | 785 | 0.660 |
| complex_responses | 109 | 198 | 307 | 0.645 |
| context_seeking | 75 | 435 | 510 | 0.853 |
| emergency_referrals | 4 | 440 | 444 | 0.991 |
| global_health | 223 | 451 | 674 | 0.669 |
| health_data_tasks | 43 | 424 | 467 | 0.908 |
| hedging | 229 | 611 | 840 | 0.727 |


**Physician-category shift** (sorted by share retained):

| physician_category | out_S2 | in_S2 | total | share_in |
|---|---|---|---|---|
| health-professional | 146 | 152 | 298 | 0.510 |
| detailed | 52 | 75 | 127 | 0.591 |
| context-matters-but-unclear | 60 | 97 | 157 | 0.618 |
| only-irreducible-uncertainty | 62 | 120 | 182 | 0.659 |
| context-matters-is-clear | 48 | 94 | 142 | 0.662 |
| no-uncertainty | 64 | 143 | 207 | 0.691 |
| simple | 43 | 106 | 149 | 0.711 |
| context-does-not-matter | 42 | 110 | 152 | 0.724 |
| none | 224 | 591 | 815 | 0.725 |
| enough-context | 47 | 160 | 207 | 0.773 |
| not-health-professional | 68 | 295 | 363 | 0.813 |
| any-reducible-uncertainty | 46 | 204 | 250 | 0.816 |
| enough-info-to-complete-task | 19 | 195 | 214 | 0.911 |
| not-enough-context | 13 | 152 | 165 | 0.921 |
| not-enough-info-to-complete-task | 12 | 161 | 173 | 0.931 |
| non-emergent | 2 | 122 | 124 | 0.984 |
| emergent | 2 | 129 | 131 | 0.985 |
| conditionally-emergent | 0 | 171 | 171 | 1.000 |


**Other models.** MedGemma (vllm/google/medgemma-27b-text-it, log 2026-07-24T12-08-49) and PLaMo (openai-api/plamo/plamo-3.0-prime, log 2026-07-16T05-23-21) were judged by openai/gpt-4.1 with a length-adjustment penalty (center 2000 chars, 0.0299 per 500 chars); GPT-5.5 and Claude Opus 4.7 were judged by openai/gpt-4o-mini without it. Same prompt_ids (4,027/4,027 verified earlier for PLaMo), different grader: scores are not comparable in one table (project rule: never mix judge models). The run continues with two models.

## 2. Tables on the S2 discovery part

### Scope corpus — target `score_rel_mean`, support ≥ 60, |effect| ≥ 0.05, max 2 conditions, up to 8 rows

**et_corpus_gpt** (target `score_rel_gpt`, n = 1850, discovery-part mean -0.0015, 18/533 eligible patterns)

| step | rule | support | support_share | mean_target | deviation | deviation_gpt | deviation_claude | deviation_mean | n_themes | perm_p | perm_p_bh |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | evidence basis = guideline/standard AND theme = communication | 61 | 0.0330 | -0.1147 | -0.1132 | -0.1132 | -0.0744 | -0.0938 | 1 | 0.0012 | 0.0096 |
| 2 | patient age = not_stated AND possible trigger = stress/exertion | 69 | 0.0373 | -0.0956 | -0.0941 | -0.0941 | -0.0825 | -0.0883 | 7 | 0.0027 | 0.0108 |
| 3 | care setting = not_stated AND theme = communication | 116 | 0.0627 | 0.0491 | 0.0507 | 0.0507 | 0.0524 | 0.0515 | 1 | 0.0337 | 0.0362 |
| 4 | episode timing = weeks months and recurring AND theme = health_data_tasks | 81 | 0.0438 | 0.0684 | 0.0699 | 0.0699 | 0.0532 | 0.0616 | 1 | 0.0140 | 0.0280 |
| 5 | episode timing = happening now/today AND possible trigger = injury/physical contact | 106 | 0.0573 | 0.0618 | 0.0633 | 0.0633 | 0.0581 | 0.0607 | 7 | 0.0127 | 0.0280 |
| 6 | care setting = home/community AND symptom course = getting worse | 80 | 0.0432 | 0.0626 | 0.0641 | 0.0641 | 0.0417 | 0.0529 | 6 | 0.0275 | 0.0362 |
| 7 | care setting = hospital/emergency care AND intervention type = procedure/device | 80 | 0.0432 | -0.0650 | -0.0635 | -0.0635 | -0.0882 | -0.0759 | 7 | 0.0269 | 0.0362 |
| 8 | symptom course = stable/improving AND intervention type = no intervention | 69 | 0.0373 | -0.0666 | -0.0651 | -0.0651 | -0.0491 | -0.0571 | 6 | 0.0362 | 0.0362 |

**et_corpus_claude** (target `score_rel_claude`, n = 1850, discovery-part mean -0.0029, 24/533 eligible patterns)

| step | rule | support | support_share | mean_target | deviation | deviation_gpt | deviation_claude | deviation_mean | n_themes | perm_p | perm_p_bh |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | care setting = hospital/emergency care AND intervention type = procedure/device | 80 | 0.0432 | -0.0912 | -0.0882 | -0.0635 | -0.0882 | -0.0759 | 7 | 0.0028 | 0.0107 |
| 2 | patient age = 18 to 64 AND theme = health_data_tasks | 64 | 0.0346 | 0.0943 | 0.0973 | 0.0614 | 0.0973 | 0.0793 | 1 | 0.0034 | 0.0107 |
| 3 | possible trigger = injury/physical contact AND care setting = home/community | 89 | 0.0481 | 0.0777 | 0.0806 | 0.0323 | 0.0806 | 0.0565 | 7 | 0.0040 | 0.0107 |
| 4 | episode timing = not_stated AND theme = communication | 71 | 0.0384 | 0.0725 | 0.0754 | 0.0235 | 0.0754 | 0.0495 | 1 | 0.0161 | 0.0161 |
| 5 | intervention type = medicine/supplement AND theme = communication | 62 | 0.0335 | -0.0839 | -0.0810 | -0.0690 | -0.0810 | -0.0750 | 1 | 0.0154 | 0.0161 |
| 6 | possible trigger = stress/exertion | 91 | 0.0492 | -0.0724 | -0.0695 | -0.0749 | -0.0695 | -0.0722 | 7 | 0.0114 | 0.0161 |
| 7 | episode timing = weeks months and recurring AND symptom course = getting worse | 70 | 0.0378 | 0.0769 | 0.0798 | 0.0681 | 0.0798 | 0.0739 | 7 | 0.0110 | 0.0161 |
| 8 | symptom course = stable/improving AND intervention type = behavior/self-care | 80 | 0.0432 | 0.0682 | 0.0711 | 0.0363 | 0.0711 | 0.0537 | 6 | 0.0153 | 0.0161 |

**et_corpus_mean** (target `score_rel_mean`, n = 1850, discovery-part mean -0.0022, 19/533 eligible patterns)

| step | rule | support | support_share | mean_target | deviation | deviation_gpt | deviation_claude | deviation_mean | n_themes | perm_p | perm_p_bh |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | patient age = not_stated AND possible trigger = stress/exertion | 69 | 0.0373 | -0.0905 | -0.0883 | -0.0941 | -0.0825 | -0.0883 | 7 | 0.0020 | 0.0092 |
| 2 | evidence basis = guideline/standard AND theme = communication | 61 | 0.0330 | -0.0960 | -0.0938 | -0.1132 | -0.0744 | -0.0938 | 1 | 0.0023 | 0.0092 |
| 3 | care setting = not_stated AND theme = communication | 116 | 0.0627 | 0.0493 | 0.0515 | 0.0507 | 0.0524 | 0.0515 | 1 | 0.0183 | 0.0209 |
| 4 | care setting = hospital/emergency care AND intervention type = procedure/device | 80 | 0.0432 | -0.0781 | -0.0759 | -0.0635 | -0.0882 | -0.0759 | 7 | 0.0046 | 0.0123 |
| 5 | episode timing = happening now/today AND possible trigger = injury/physical contact | 106 | 0.0573 | 0.0585 | 0.0607 | 0.0633 | 0.0581 | 0.0607 | 7 | 0.0083 | 0.0131 |
| 6 | patient age = 18 to 64 AND theme = health_data_tasks | 64 | 0.0346 | 0.0771 | 0.0793 | 0.0614 | 0.0973 | 0.0793 | 1 | 0.0098 | 0.0131 |
| 7 | episode timing = weeks months and recurring AND symptom course = getting worse | 70 | 0.0378 | 0.0717 | 0.0739 | 0.0681 | 0.0798 | 0.0739 | 7 | 0.0097 | 0.0131 |
| 8 | symptom course = stable/improving AND intervention type = behavior/self-care | 80 | 0.0432 | 0.0515 | 0.0537 | 0.0363 | 0.0711 | 0.0537 | 6 | 0.0434 | 0.0434 |

### Scope theme:emergency_referrals — target `score_mean`, support ≥ 20, |effect| ≥ 0.08, max 2 conditions, up to 8 rows

**et_theme_emergency_referrals_gpt** (target `score_gpt`, n = 268, discovery-part mean 0.6005, 16/206 eligible patterns)

| step | rule | support | support_share | mean_target | deviation | deviation_gpt | deviation_claude | deviation_mean | n_themes | perm_p | perm_p_bh |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | episode timing = happening now/today AND intervention type = not_stated | 26 | 0.0970 | 0.7641 | 0.1636 | 0.1636 | 0.1617 | 0.1627 | 1 | 0.0025 | 0.0176 |
| 2 | care setting = home/community AND symptom course = getting worse | 26 | 0.0970 | 0.7611 | 0.1607 | 0.1607 | 0.1030 | 0.1318 | 1 | 0.0044 | 0.0176 |
| 3 | possible trigger = medicine/medical treatment | 21 | 0.0784 | 0.7424 | 0.1419 | 0.1419 | 0.1528 | 0.1474 | 1 | 0.0232 | 0.0413 |
| 4 | possible trigger = not_stated AND symptom course = stable/improving | 30 | 0.1119 | 0.7017 | 0.1013 | 0.1013 | 0.0743 | 0.0878 | 1 | 0.0458 | 0.0599 |
| 5 | care setting = not_stated AND intervention type = no intervention | 23 | 0.0858 | 0.7038 | 0.1033 | 0.1033 | 0.0772 | 0.0902 | 1 | 0.0855 | 0.0855 |
| 6 | episode timing = happening now/today AND care setting = not_stated | 42 | 0.1567 | 0.6823 | 0.0818 | 0.0818 | 0.0526 | 0.0672 | 1 | 0.0524 | 0.0599 |
| 7 | possible trigger = environment food and travel | 22 | 0.0821 | 0.4488 | -0.1516 | -0.1516 | -0.0594 | -0.1055 | 1 | 0.0108 | 0.0288 |
| 8 | care setting = home/community AND intervention type = not_stated | 22 | 0.0821 | 0.7343 | 0.1338 | 0.1338 | 0.0920 | 0.1129 | 1 | 0.0258 | 0.0413 |

**et_theme_emergency_referrals_claude** (target `score_claude`, n = 268, discovery-part mean 0.5961, 18/206 eligible patterns)

| step | rule | support | support_share | mean_target | deviation | deviation_gpt | deviation_claude | deviation_mean | n_themes | perm_p | perm_p_bh |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | possible trigger = not_stated AND intervention type = procedure/device | 31 | 0.1157 | 0.4141 | -0.1821 | -0.0643 | -0.1821 | -0.1232 | 1 | 0.0005 | 0.0040 |
| 2 | episode timing = happening now/today AND care setting = hospital/emergency care | 31 | 0.1157 | 0.4451 | -0.1510 | -0.0962 | -0.1510 | -0.1236 | 1 | 0.0051 | 0.0147 |
| 3 | episode timing = happening now/today AND intervention type = not_stated | 26 | 0.0970 | 0.7579 | 0.1617 | 0.1636 | 0.1617 | 0.1627 | 1 | 0.0055 | 0.0147 |
| 4 | possible trigger = medicine/medical treatment | 21 | 0.0784 | 0.7490 | 0.1528 | 0.1419 | 0.1528 | 0.1474 | 1 | 0.0211 | 0.0387 |
| 5 | episode timing = weeks months and recurring AND possible trigger = not_stated | 39 | 0.1455 | 0.6791 | 0.0830 | 0.0520 | 0.0830 | 0.0675 | 1 | 0.0758 | 0.0872 |
| 6 | care setting = home/community AND symptom course = getting worse | 26 | 0.0970 | 0.6992 | 0.1030 | 0.1607 | 0.1030 | 0.1318 | 1 | 0.0763 | 0.0872 |
| 7 | symptom course = getting worse AND intervention type = procedure/device | 28 | 0.1045 | 0.4718 | -0.1243 | -0.0547 | -0.1243 | -0.0895 | 1 | 0.0242 | 0.0387 |
| 8 | care setting = home/community AND intervention type = not_stated | 22 | 0.0821 | 0.6881 | 0.0920 | 0.1338 | 0.0920 | 0.1129 | 1 | 0.1534 | 0.1534 |

**et_theme_emergency_referrals_mean** (target `score_mean`, n = 268, discovery-part mean 0.5983, 19/206 eligible patterns)

| step | rule | support | support_share | mean_target | deviation | deviation_gpt | deviation_claude | deviation_mean | n_themes | perm_p | perm_p_bh |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | episode timing = happening now/today AND intervention type = not_stated | 26 | 0.0970 | 0.7610 | 0.1627 | 0.1636 | 0.1617 | 0.1627 | 1 | 0.0022 | 0.0176 |
| 2 | possible trigger = medicine/medical treatment | 21 | 0.0784 | 0.7457 | 0.1474 | 0.1419 | 0.1528 | 0.1474 | 1 | 0.0147 | 0.0235 |
| 3 | episode timing = happening now/today AND care setting = hospital/emergency care | 31 | 0.1157 | 0.4747 | -0.1236 | -0.0962 | -0.1510 | -0.1236 | 1 | 0.0111 | 0.0235 |
| 4 | care setting = home/community AND symptom course = getting worse | 26 | 0.0970 | 0.7301 | 0.1318 | 0.1607 | 0.1030 | 0.1318 | 1 | 0.0121 | 0.0235 |
| 5 | possible trigger = not_stated AND symptom course = stable/improving | 30 | 0.1119 | 0.6861 | 0.0878 | 0.1013 | 0.0743 | 0.0878 | 1 | 0.0791 | 0.1055 |
| 6 | possible trigger = not_stated AND intervention type = procedure/device | 31 | 0.1157 | 0.4751 | -0.1232 | -0.0643 | -0.1821 | -0.1232 | 1 | 0.0102 | 0.0235 |
| 7 | care setting = not_stated AND intervention type = no intervention | 23 | 0.0858 | 0.6885 | 0.0902 | 0.1033 | 0.0772 | 0.0902 | 1 | 0.1113 | 0.1234 |
| 8 | episode timing = not_stated | 26 | 0.0970 | 0.5161 | -0.0822 | -0.1116 | -0.0529 | -0.0822 | 1 | 0.1234 | 0.1234 |

### Scope theme:communication — target `score_mean`, support ≥ 20, |effect| ≥ 0.08, max 2 conditions, up to 8 rows

**et_theme_communication_gpt** (target `score_gpt`, n = 314, discovery-part mean 0.6133, 18/268 eligible patterns)

| step | rule | support | support_share | mean_target | deviation | deviation_gpt | deviation_claude | deviation_mean | n_themes | perm_p | perm_p_bh |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | evidence basis = guideline/standard | 61 | 0.1943 | 0.4963 | -0.1169 | -0.1169 | -0.0857 | -0.1013 | 1 | 0.0008 | 0.0064 |
| 2 | symptom course = not_stated AND intervention type = no intervention | 31 | 0.0987 | 0.7593 | 0.1460 | 0.1460 | 0.1274 | 0.1367 | 1 | 0.0048 | 0.0192 |
| 3 | episode timing = happening now/today AND care setting = home/community | 39 | 0.1242 | 0.5230 | -0.0903 | -0.0903 | -0.1049 | -0.0976 | 1 | 0.0426 | 0.0568 |
| 4 | symptom course = not_stated AND intervention type = not_stated | 25 | 0.0796 | 0.4720 | -0.1413 | -0.1413 | -0.0887 | -0.1150 | 1 | 0.0152 | 0.0304 |
| 5 | symptom course = getting worse AND evidence basis = no outside basis | 23 | 0.0732 | 0.7712 | 0.1579 | 0.1579 | 0.1086 | 0.1332 | 1 | 0.0084 | 0.0224 |
| 6 | patient age = not_stated AND intervention type = procedure/device | 46 | 0.1465 | 0.6981 | 0.0848 | 0.0848 | 0.1255 | 0.1052 | 1 | 0.0412 | 0.0568 |
| 7 | possible trigger = not_stated AND care setting = clinic/outpatient care | 22 | 0.0701 | 0.5087 | -0.1046 | -0.1046 | -0.0513 | -0.0780 | 1 | 0.0947 | 0.0947 |
| 8 | patient age = not_stated AND possible trigger = injury/physical contact | 20 | 0.0637 | 0.7396 | 0.1263 | 0.1263 | 0.1084 | 0.1174 | 1 | 0.0501 | 0.0573 |

**et_theme_communication_claude** (target `score_claude`, n = 314, discovery-part mean 0.5965, 28/268 eligible patterns)

| step | rule | support | support_share | mean_target | deviation | deviation_gpt | deviation_claude | deviation_mean | n_themes | perm_p | perm_p_bh |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | intervention type = medicine/supplement AND evidence basis = guideline/standard | 24 | 0.0764 | 0.4010 | -0.1955 | -0.1409 | -0.1955 | -0.1682 | 1 | 0.0006 | 0.0048 |
| 2 | patient age = not_stated AND intervention type = procedure/device | 46 | 0.1465 | 0.7220 | 0.1255 | 0.0848 | 0.1255 | 0.1052 | 1 | 0.0036 | 0.0144 |
| 3 | symptom course = not_stated AND intervention type = no intervention | 31 | 0.0987 | 0.7239 | 0.1274 | 0.1460 | 0.1274 | 0.1367 | 1 | 0.0177 | 0.0354 |
| 4 | episode timing = happening now/today AND symptom course = not_stated | 61 | 0.1943 | 0.5071 | -0.0895 | -0.0631 | -0.0895 | -0.0763 | 1 | 0.0157 | 0.0354 |
| 5 | care setting = home/community AND symptom course = stable/improving | 25 | 0.0796 | 0.4667 | -0.1298 | -0.0656 | -0.1298 | -0.0977 | 1 | 0.0338 | 0.0541 |
| 6 | possible trigger = environment food and travel | 21 | 0.0669 | 0.4629 | -0.1337 | -0.0363 | -0.1337 | -0.0850 | 1 | 0.0437 | 0.0583 |
| 7 | patient age = under 18 AND symptom course = not_stated | 20 | 0.0637 | 0.4974 | -0.0991 | -0.0701 | -0.0991 | -0.0846 | 1 | 0.1526 | 0.1744 |
| 8 | episode timing = weeks months and recurring AND intervention type = no intervention | 21 | 0.0669 | 0.5076 | -0.0889 | -0.0687 | -0.0889 | -0.0788 | 1 | 0.1840 | 0.1840 |

**et_theme_communication_mean** (target `score_mean`, n = 314, discovery-part mean 0.6049, 22/268 eligible patterns)

| step | rule | support | support_share | mean_target | deviation | deviation_gpt | deviation_claude | deviation_mean | n_themes | perm_p | perm_p_bh |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | intervention type = medicine/supplement AND evidence basis = guideline/standard | 24 | 0.0764 | 0.4367 | -0.1682 | -0.1409 | -0.1955 | -0.1682 | 1 | 0.0022 | 0.0100 |
| 2 | symptom course = not_stated AND intervention type = no intervention | 31 | 0.0987 | 0.7416 | 0.1367 | 0.1460 | 0.1274 | 0.1367 | 1 | 0.0056 | 0.0149 |
| 3 | patient age = not_stated AND intervention type = procedure/device | 46 | 0.1465 | 0.7101 | 0.1052 | 0.0848 | 0.1255 | 0.1052 | 1 | 0.0078 | 0.0156 |
| 4 | symptom course = getting worse AND evidence basis = no outside basis | 23 | 0.0732 | 0.7382 | 0.1332 | 0.1579 | 0.1086 | 0.1332 | 1 | 0.0246 | 0.0328 |
| 5 | episode timing = happening now/today AND care setting = home/community | 39 | 0.1242 | 0.5073 | -0.0976 | -0.0903 | -0.1049 | -0.0976 | 1 | 0.0246 | 0.0328 |
| 6 | patient age = under 18 AND symptom course = not_stated | 20 | 0.0637 | 0.5203 | -0.0846 | -0.0701 | -0.0991 | -0.0846 | 1 | 0.1865 | 0.1865 |
| 7 | possible trigger = environment food and travel | 21 | 0.0669 | 0.5199 | -0.0850 | -0.0363 | -0.1337 | -0.0850 | 1 | 0.1673 | 0.1865 |
| 8 | evidence basis = guideline/standard | 61 | 0.1943 | 0.5036 | -0.1013 | -0.1169 | -0.0857 | -0.1013 | 1 | 0.0025 | 0.0100 |

## 3. Preregistered rules and confirmation

Preregistration rule: Pool: distinct rules of the 2-condition tables gpt/claude/mean of the scope. Eligible: deviation on discovery has the same sign for gpt and claude. Rank: number of the three tables containing the rule (desc), then min(|dev gpt|, |dev claude|) (desc). Take up to max_rules. No diff fill.

Confirmation on the S2 part of the confirmation split: same sign as on discovery, support ≥ 40 (corpus) / ≥ 12 (theme), 95% bootstrap CI (2000 resamples) of the rule mean excludes the confirmation-part mean. Judged on the scope target; gpt / claude columns apply the same criterion per model.

### corpus — 2 of 10 preregistered rules confirmed

| id | rule | tables | support_disc | dev_disc | support_conf | dev_conf | ci_low | ci_high | conf_part_mean | shrinkage | sign_same | support_ok | ci_excludes_mean | confirmed | gpt_confirmed | claude_confirmed | perm_p_conf |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | care setting = hospital/emergency care AND intervention type = procedure/device | gpt,claude,mean | 80 | -0.0759 | 52 | -0.0852 | -0.1539 | -0.0241 | -0.0023 | 1.1234 | True | True | True | True | True | True | 0.0130 |
| 2 | patient age = not_stated AND possible trigger = stress/exertion | gpt,mean | 69 | -0.0883 | 47 | 0.0285 | -0.0307 | 0.0841 | -0.0023 | -0.3227 | False | True | False | False | False | False | 0.4258 |
| 3 | evidence basis = guideline/standard AND theme = communication | gpt,mean | 61 | -0.0938 | 43 | -0.0791 | -0.1566 | -0.0009 | -0.0023 | 0.8430 | True | True | False | False | True | False | 0.0319 |
| 4 | episode timing = weeks months and recurring AND symptom course = getting worse | claude,mean | 70 | 0.0739 | 47 | 0.0404 | -0.0355 | 0.1149 | -0.0023 | 0.5465 | True | True | False | False | False | False | 0.2549 |
| 5 | patient age = 18 to 64 AND theme = health_data_tasks | claude,mean | 64 | 0.0793 | 36 | -0.0223 | -0.1229 | 0.0748 | -0.0023 | -0.2817 | False | False | False | False | False | False | 0.5851 |
| 6 | episode timing = happening now/today AND possible trigger = injury/physical contact | gpt,mean | 106 | 0.0607 | 74 | 0.0273 | -0.0258 | 0.0734 | -0.0023 | 0.4496 | True | True | False | False | False | False | 0.3295 |
| 7 | care setting = not_stated AND theme = communication | gpt,mean | 116 | 0.0515 | 75 | 0.1058 | 0.0377 | 0.1687 | -0.0023 | 2.0532 | True | True | True | True | True | True | 0.0002 |
| 8 | symptom course = stable/improving AND intervention type = behavior/self-care | claude,mean | 80 | 0.0537 | 48 | 0.0051 | -0.0474 | 0.0532 | -0.0023 | 0.0945 | True | True | False | False | False | False | 0.8844 |
| 9 | possible trigger = stress/exertion | claude | 91 | -0.0722 | 61 | 0.0154 | -0.0431 | 0.0663 | -0.0023 | -0.2133 | False | True | False | False | False | False | 0.6226 |
| 10 | intervention type = medicine/supplement AND theme = communication | claude | 62 | -0.0750 | 45 | 0.0405 | -0.0486 | 0.1238 | -0.0023 | -0.5406 | False | True | False | False | False | False | 0.2771 |

### theme:emergency_referrals — 2 of 6 preregistered rules confirmed

| id | rule | tables | support_disc | dev_disc | support_conf | dev_conf | ci_low | ci_high | conf_part_mean | shrinkage | sign_same | support_ok | ci_excludes_mean | confirmed | gpt_confirmed | claude_confirmed | perm_p_conf |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | episode timing = happening now/today AND intervention type = not_stated | gpt,claude,mean | 26 | 0.1627 | 15 | 0.0472 | 0.4518 | 0.8061 | 0.5849 | 0.2900 | True | True | False | False | False | False | 0.5086 |
| 2 | possible trigger = medicine/medical treatment | gpt,claude,mean | 21 | 0.1474 | 14 | -0.0020 | 0.4244 | 0.7400 | 0.5849 | -0.0137 | False | True | False | False | False | False | 0.9770 |
| 3 | care setting = home/community AND symptom course = getting worse | gpt,claude,mean | 26 | 0.1318 | 8 | -0.0375 | 0.3697 | 0.7159 | 0.5849 | -0.2844 | False | False | False | False | False | False | 0.7129 |
| 4 | episode timing = happening now/today AND care setting = hospital/emergency care | claude,mean | 31 | -0.1236 | 19 | -0.1820 | 0.3086 | 0.5020 | 0.5849 | 1.4725 | True | True | True | True | True | True | 0.0044 |
| 5 | care setting = home/community AND intervention type = not_stated | gpt,claude | 22 | 0.1129 | 13 | 0.1717 | 0.6514 | 0.8590 | 0.5849 | 1.5204 | True | True | True | True | True | True | 0.0251 |
| 6 | care setting = not_stated AND intervention type = no intervention | gpt,mean | 23 | 0.0902 | 23 | -0.0556 | 0.4046 | 0.6566 | 0.5849 | -0.6165 | False | True | False | False | False | False | 0.3207 |

### theme:communication — 1 of 6 preregistered rules confirmed

| id | rule | tables | support_disc | dev_disc | support_conf | dev_conf | ci_low | ci_high | conf_part_mean | shrinkage | sign_same | support_ok | ci_excludes_mean | confirmed | gpt_confirmed | claude_confirmed | perm_p_conf |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | symptom course = not_stated AND intervention type = no intervention | gpt,claude,mean | 31 | 0.1367 | 19 | 0.0736 | 0.5417 | 0.7909 | 0.5979 | 0.5384 | True | True | False | False | False | False | 0.2342 |
| 2 | patient age = not_stated AND intervention type = procedure/device | gpt,claude,mean | 46 | 0.1052 | 21 | -0.0333 | 0.4758 | 0.6602 | 0.5979 | -0.3163 | False | True | False | False | False | False | 0.5724 |
| 3 | intervention type = medicine/supplement AND evidence basis = guideline/standard | claude,mean | 24 | -0.1682 | 13 | -0.0041 | 0.4515 | 0.7474 | 0.5979 | 0.0241 | True | True | False | False | False | False | 0.9588 |
| 4 | symptom course = getting worse AND evidence basis = no outside basis | gpt,mean | 23 | 0.1332 | 11 | 0.1041 | 0.5254 | 0.8645 | 0.5979 | 0.7812 | True | False | False | False | False | False | 0.2214 |
| 5 | episode timing = happening now/today AND care setting = home/community | gpt,mean | 39 | -0.0976 | 32 | -0.0809 | 0.4188 | 0.6136 | 0.5979 | 0.8285 | True | True | False | False | False | False | 0.0832 |
| 6 | evidence basis = guideline/standard | gpt,mean | 61 | -0.1013 | 43 | -0.0796 | 0.4408 | 0.5928 | 0.5979 | 0.7859 | True | True | True | True | True | False | 0.0391 |

## 4. k of m per table

| table | confirmed (k) | rows (m) |
|---|---|---|
| et_corpus_gpt | 3 | 8 |
| et_corpus_claude | 1 | 8 |
| et_corpus_mean | 3 | 8 |
| et_theme_emergency_referrals_gpt | 1 | 8 |
| et_theme_emergency_referrals_claude | 3 | 8 |
| et_theme_emergency_referrals_mean | 1 | 8 |
| et_theme_communication_gpt | 2 | 8 |
| et_theme_communication_claude | 0 | 8 |
| et_theme_communication_mean | 0 | 8 |


**et_corpus_gpt** on confirmation

| step | rule | support_disc | dev_disc | support_conf | dev_conf | ci_low | ci_high | shrinkage | confirmed | perm_p_conf |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | evidence basis = guideline/standard AND theme = communication | 61 | -0.1132 | 43 | -0.0931 | -0.1725 | -0.0204 | 0.8225 | True | 0.0186 |
| 2 | patient age = not_stated AND possible trigger = stress/exertion | 69 | -0.0941 | 47 | 0.0498 | -0.0192 | 0.1108 | -0.5298 | False | 0.1956 |
| 3 | care setting = not_stated AND theme = communication | 116 | 0.0507 | 75 | 0.0958 | 0.0301 | 0.1568 | 1.8922 | True | 0.0017 |
| 4 | episode timing = weeks months and recurring AND theme = health_data_tasks | 81 | 0.0699 | 54 | -0.0278 | -0.0980 | 0.0435 | -0.3968 | False | 0.4461 |
| 5 | episode timing = happening now/today AND possible trigger = injury/physical contact | 106 | 0.0633 | 74 | 0.0296 | -0.0261 | 0.0822 | 0.4676 | False | 0.3318 |
| 6 | care setting = home/community AND symptom course = getting worse | 80 | 0.0641 | 37 | 0.0085 | -0.0815 | 0.1022 | 0.1329 | False | 0.8403 |
| 7 | care setting = hospital/emergency care AND intervention type = procedure/device | 80 | -0.0635 | 52 | -0.0765 | -0.1515 | -0.0059 | 1.2041 | True | 0.0342 |
| 8 | symptom course = stable/improving AND intervention type = no intervention | 69 | -0.0651 | 60 | 0.0044 | -0.0656 | 0.0717 | -0.0681 | False | 0.8975 |


**et_corpus_claude** on confirmation

| step | rule | support_disc | dev_disc | support_conf | dev_conf | ci_low | ci_high | shrinkage | confirmed | perm_p_conf |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | care setting = hospital/emergency care AND intervention type = procedure/device | 80 | -0.0882 | 52 | -0.0940 | -0.1669 | -0.0290 | 1.0654 | True | 0.0115 |
| 2 | patient age = 18 to 64 AND theme = health_data_tasks | 64 | 0.0973 | 36 | -0.0278 | -0.1402 | 0.0832 | -0.2862 | False | 0.5374 |
| 3 | possible trigger = injury/physical contact AND care setting = home/community | 89 | 0.0806 | 69 | 0.0107 | -0.0529 | 0.0656 | 0.1321 | False | 0.7432 |
| 4 | episode timing = not_stated AND theme = communication | 71 | 0.0754 | 47 | -0.0068 | -0.0968 | 0.0692 | -0.0896 | False | 0.8561 |
| 5 | intervention type = medicine/supplement AND theme = communication | 62 | -0.0810 | 45 | 0.0453 | -0.0535 | 0.1362 | -0.5596 | False | 0.2499 |
| 6 | possible trigger = stress/exertion | 91 | -0.0695 | 61 | -0.0038 | -0.0651 | 0.0553 | 0.0551 | False | 0.9123 |
| 7 | episode timing = weeks months and recurring AND symptom course = getting worse | 70 | 0.0798 | 47 | 0.0510 | -0.0339 | 0.1268 | 0.6390 | False | 0.1873 |
| 8 | symptom course = stable/improving AND intervention type = behavior/self-care | 80 | 0.0711 | 48 | -0.0055 | -0.0763 | 0.0492 | -0.0776 | False | 0.8769 |


**et_corpus_mean** on confirmation

| step | rule | support_disc | dev_disc | support_conf | dev_conf | ci_low | ci_high | shrinkage | confirmed | perm_p_conf |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | patient age = not_stated AND possible trigger = stress/exertion | 69 | -0.0883 | 47 | 0.0285 | -0.0331 | 0.0842 | -0.3227 | False | 0.4186 |
| 2 | evidence basis = guideline/standard AND theme = communication | 61 | -0.0938 | 43 | -0.0791 | -0.1581 | -0.0031 | 0.8430 | True | 0.0337 |
| 3 | care setting = not_stated AND theme = communication | 116 | 0.0515 | 75 | 0.1058 | 0.0374 | 0.1694 | 2.0532 | True | 0.0003 |
| 4 | care setting = hospital/emergency care AND intervention type = procedure/device | 80 | -0.0759 | 52 | -0.0852 | -0.1531 | -0.0216 | 1.1234 | True | 0.0117 |
| 5 | episode timing = happening now/today AND possible trigger = injury/physical contact | 106 | 0.0607 | 74 | 0.0273 | -0.0267 | 0.0748 | 0.4496 | False | 0.3216 |
| 6 | patient age = 18 to 64 AND theme = health_data_tasks | 64 | 0.0793 | 36 | -0.0223 | -0.1225 | 0.0829 | -0.2817 | False | 0.5761 |
| 7 | episode timing = weeks months and recurring AND symptom course = getting worse | 70 | 0.0739 | 47 | 0.0404 | -0.0387 | 0.1125 | 0.5465 | False | 0.2512 |
| 8 | symptom course = stable/improving AND intervention type = behavior/self-care | 80 | 0.0537 | 48 | 0.0051 | -0.0512 | 0.0544 | 0.0945 | False | 0.8854 |


**et_theme_emergency_referrals_gpt** on confirmation

| step | rule | support_disc | dev_disc | support_conf | dev_conf | ci_low | ci_high | shrinkage | confirmed | perm_p_conf |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | episode timing = happening now/today AND intervention type = not_stated | 26 | 0.1636 | 15 | 0.0063 | 0.4054 | 0.7658 | 0.0383 | False | 0.9322 |
| 2 | care setting = home/community AND symptom course = getting worse | 26 | 0.1607 | 8 | -0.0837 | 0.3159 | 0.6873 | -0.5212 | False | 0.4252 |
| 3 | possible trigger = medicine/medical treatment | 21 | 0.1419 | 14 | 0.0325 | 0.4469 | 0.8013 | 0.2288 | False | 0.6776 |
| 4 | possible trigger = not_stated AND symptom course = stable/improving | 30 | 0.1013 | 22 | 0.1096 | 0.5784 | 0.8170 | 1.0822 | False | 0.0690 |
| 5 | care setting = not_stated AND intervention type = no intervention | 23 | 0.1033 | 23 | -0.0879 | 0.3665 | 0.6425 | -0.8508 | False | 0.1383 |
| 6 | episode timing = happening now/today AND care setting = not_stated | 42 | 0.0818 | 26 | 0.0314 | 0.4858 | 0.7518 | 0.3843 | False | 0.5641 |
| 7 | possible trigger = environment food and travel | 22 | -0.1516 | 16 | -0.0143 | 0.4559 | 0.6890 | 0.0942 | False | 0.8457 |
| 8 | care setting = home/community AND intervention type = not_stated | 22 | 0.1338 | 13 | 0.1247 | 0.5992 | 0.8355 | 0.9316 | True | 0.1232 |


**et_theme_emergency_referrals_claude** on confirmation

| step | rule | support_disc | dev_disc | support_conf | dev_conf | ci_low | ci_high | shrinkage | confirmed | perm_p_conf |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | possible trigger = not_stated AND intervention type = procedure/device | 31 | -0.1821 | 25 | -0.0473 | 0.4232 | 0.6581 | 0.2597 | False | 0.3997 |
| 2 | episode timing = happening now/today AND care setting = hospital/emergency care | 31 | -0.1510 | 19 | -0.2127 | 0.2627 | 0.4745 | 1.4083 | True | 0.0008 |
| 3 | episode timing = happening now/today AND intervention type = not_stated | 26 | 0.1617 | 15 | 0.0881 | 0.4613 | 0.8564 | 0.5448 | False | 0.2406 |
| 4 | possible trigger = medicine/medical treatment | 21 | 0.1528 | 14 | -0.0365 | 0.3843 | 0.7114 | -0.2387 | False | 0.6361 |
| 5 | episode timing = weeks months and recurring AND possible trigger = not_stated | 39 | 0.0830 | 36 | 0.0734 | 0.5603 | 0.7537 | 0.8842 | False | 0.1082 |
| 6 | care setting = home/community AND symptom course = getting worse | 26 | 0.1030 | 8 | 0.0088 | 0.4246 | 0.7548 | 0.0850 | False | 0.9389 |
| 7 | symptom course = getting worse AND intervention type = procedure/device | 28 | -0.1243 | 13 | -0.2330 | 0.2581 | 0.4313 | 1.8743 | True | 0.0035 |
| 8 | care setting = home/community AND intervention type = not_stated | 22 | 0.0920 | 13 | 0.2187 | 0.6491 | 0.9206 | 2.3770 | True | 0.0066 |


**et_theme_emergency_referrals_mean** on confirmation

| step | rule | support_disc | dev_disc | support_conf | dev_conf | ci_low | ci_high | shrinkage | confirmed | perm_p_conf |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | episode timing = happening now/today AND intervention type = not_stated | 26 | 0.1627 | 15 | 0.0472 | 0.4475 | 0.8146 | 0.2900 | False | 0.5111 |
| 2 | possible trigger = medicine/medical treatment | 21 | 0.1474 | 14 | -0.0020 | 0.4165 | 0.7424 | -0.0137 | False | 0.9781 |
| 3 | episode timing = happening now/today AND care setting = hospital/emergency care | 31 | -0.1236 | 19 | -0.1820 | 0.3049 | 0.5012 | 1.4725 | True | 0.0033 |
| 4 | care setting = home/community AND symptom course = getting worse | 26 | 0.1318 | 8 | -0.0375 | 0.3610 | 0.7111 | -0.2844 | False | 0.7105 |
| 5 | possible trigger = not_stated AND symptom course = stable/improving | 30 | 0.0878 | 22 | 0.0871 | 0.5531 | 0.7829 | 0.9925 | False | 0.1296 |
| 6 | possible trigger = not_stated AND intervention type = procedure/device | 31 | -0.1232 | 25 | -0.0052 | 0.4734 | 0.6896 | 0.0420 | False | 0.9224 |
| 7 | care setting = not_stated AND intervention type = no intervention | 23 | 0.0902 | 23 | -0.0556 | 0.4093 | 0.6512 | -0.6165 | False | 0.3288 |
| 8 | episode timing = not_stated | 26 | -0.0822 | 13 | -0.0002 | 0.3903 | 0.7774 | 0.0027 | False | 0.9976 |


**et_theme_communication_gpt** on confirmation

| step | rule | support_disc | dev_disc | support_conf | dev_conf | ci_low | ci_high | shrinkage | confirmed | perm_p_conf |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | evidence basis = guideline/standard | 61 | -0.1169 | 43 | -0.0962 | 0.4440 | 0.5946 | 0.8229 | True | 0.0172 |
| 2 | symptom course = not_stated AND intervention type = no intervention | 31 | 0.1460 | 19 | 0.0651 | 0.5609 | 0.7926 | 0.4461 | False | 0.3207 |
| 3 | episode timing = happening now/today AND care setting = home/community | 39 | -0.0903 | 32 | -0.0708 | 0.4353 | 0.6473 | 0.7843 | False | 0.1418 |
| 4 | symptom course = not_stated AND intervention type = not_stated | 25 | -0.1413 | 10 | -0.0383 | 0.3985 | 0.7502 | 0.2711 | False | 0.6751 |
| 5 | symptom course = getting worse AND evidence basis = no outside basis | 23 | 0.1579 | 11 | 0.0965 | 0.5393 | 0.8549 | 0.6112 | False | 0.2727 |
| 6 | patient age = not_stated AND intervention type = procedure/device | 46 | 0.0848 | 21 | -0.0296 | 0.4727 | 0.6951 | -0.3494 | False | 0.6283 |
| 7 | possible trigger = not_stated AND care setting = clinic/outpatient care | 22 | -0.1046 | 12 | -0.1872 | 0.2604 | 0.5911 | 1.7899 | True | 0.0235 |
| 8 | patient age = not_stated AND possible trigger = injury/physical contact | 20 | 0.1263 | 12 | -0.0833 | 0.3140 | 0.7295 | -0.6589 | False | 0.3250 |


**et_theme_communication_claude** on confirmation

| step | rule | support_disc | dev_disc | support_conf | dev_conf | ci_low | ci_high | shrinkage | confirmed | perm_p_conf |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | intervention type = medicine/supplement AND evidence basis = guideline/standard | 24 | -0.1955 | 13 | 0.0216 | 0.4555 | 0.7487 | -0.1104 | False | 0.7832 |
| 2 | patient age = not_stated AND intervention type = procedure/device | 46 | 0.1255 | 21 | -0.0369 | 0.4530 | 0.6417 | -0.2938 | False | 0.5540 |
| 3 | symptom course = not_stated AND intervention type = no intervention | 31 | 0.1274 | 19 | 0.0821 | 0.5142 | 0.7940 | 0.6441 | False | 0.2162 |
| 4 | episode timing = happening now/today AND symptom course = not_stated | 61 | -0.0895 | 39 | -0.0158 | 0.4645 | 0.6640 | 0.1762 | False | 0.7293 |
| 5 | care setting = home/community AND symptom course = stable/improving | 25 | -0.1298 | 21 | -0.0509 | 0.4248 | 0.6368 | 0.3925 | False | 0.4223 |
| 6 | possible trigger = environment food and travel | 21 | -0.1337 | 17 | 0.0043 | 0.4635 | 0.7099 | -0.0324 | False | 0.9518 |
| 7 | patient age = under 18 AND symptom course = not_stated | 20 | -0.0991 | 13 | 0.0420 | 0.4354 | 0.7958 | -0.4235 | False | 0.6095 |
| 8 | episode timing = weeks months and recurring AND intervention type = no intervention | 21 | -0.0889 | 7 | -0.1098 | 0.3037 | 0.6534 | 1.2349 | False | 0.3263 |


**et_theme_communication_mean** on confirmation

| step | rule | support_disc | dev_disc | support_conf | dev_conf | ci_low | ci_high | shrinkage | confirmed | perm_p_conf |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | intervention type = medicine/supplement AND evidence basis = guideline/standard | 24 | -0.1682 | 13 | -0.0041 | 0.4410 | 0.7433 | 0.0241 | False | 0.9602 |
| 2 | symptom course = not_stated AND intervention type = no intervention | 31 | 0.1367 | 19 | 0.0736 | 0.5427 | 0.7918 | 0.5384 | False | 0.2373 |
| 3 | patient age = not_stated AND intervention type = procedure/device | 46 | 0.1052 | 21 | -0.0333 | 0.4660 | 0.6656 | -0.3163 | False | 0.5801 |
| 4 | symptom course = getting worse AND evidence basis = no outside basis | 23 | 0.1332 | 11 | 0.1041 | 0.5260 | 0.8612 | 0.7812 | False | 0.2245 |
| 5 | episode timing = happening now/today AND care setting = home/community | 39 | -0.0976 | 32 | -0.0809 | 0.4258 | 0.6179 | 0.8285 | False | 0.0795 |
| 6 | patient age = under 18 AND symptom course = not_stated | 20 | -0.0846 | 13 | 0.0334 | 0.4590 | 0.7869 | -0.3953 | False | 0.6589 |
| 7 | possible trigger = environment food and travel | 21 | -0.0850 | 17 | -0.0204 | 0.4569 | 0.7008 | 0.2403 | False | 0.7557 |
| 8 | evidence basis = guideline/standard | 61 | -0.1013 | 43 | -0.0796 | 0.4402 | 0.5981 | 0.7859 | False | 0.0395 |


## 5. Confirmed rules recomputed on all S2 items of their scope (worst first)

Points = deviation × 100 in the scope target (corpus: theme-centred score_rel; theme: absolute score). Percent = deviation / mean of the clipped score of the scope's S2 items. `clipped` = score in [0,1], `raw` = unclipped score. Worst axis: per model, achieved points on the axis / total positive points (sums to the unclipped score), centred on the theme mean; row term = mean(row) - mean(all), averaged over gpt and claude; the axis with the largest term in the direction of the deviation; n = rule messages with a criterion on that axis.

### corpus (n = 3077; clipped means gpt 0.4995, claude 0.4890, mean 0.4943)

| rule | preregistered_id | confirmed_in | n_disc | n_conf | n_all_s2 | themes | mean_target_dev_pts | mean_target_dev_pct | gpt_target_dev_pts | claude_target_dev_pts | mean_clipped_dev_pts | mean_raw_dev_pts | mean_raw_dev_pct | worst_axis | worst_axis_term_pts | worst_axis_n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| evidence basis = guideline/standard AND theme = communication | 3 | gpt#1, mean#2 | 61 | 43 | 104 | 1 | -8.77 | -17.75 | -10.49 | -7.06 | 1.54 | 2.00 | 4.14 | communication_quality | -7.37 | 75 |
| care setting = hospital/emergency care AND intervention type = procedure/device | 1 | gpt#7, claude#1, mean#4, prereg#1 | 80 | 52 | 132 | 7 | -7.96 | -16.10 | -6.86 | -9.05 | -6.72 | -7.98 | -16.48 | context_awareness | -7.44 | 91 |
| care setting = not_stated AND theme = communication | 7 | gpt#3, mean#3, prereg#7 | 116 | 75 | 191 | 1 | 7.29 | 14.74 | 6.84 | 7.73 | 17.59 | 18.50 | 38.19 | communication_quality | 5.32 | 174 |

### theme:emergency_referrals (n = 440; clipped means gpt 0.5963, claude 0.5898, mean 0.5931)

| rule | preregistered_id | confirmed_in | n_disc | n_conf | n_all_s2 | themes | mean_target_dev_pts | mean_target_dev_pct | gpt_target_dev_pts | claude_target_dev_pts | mean_clipped_dev_pts | mean_raw_dev_pts | mean_raw_dev_pct | worst_axis | worst_axis_term_pts | worst_axis_n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| episode timing = happening now/today AND care setting = hospital/emergency care | 4.00 | claude#2, mean#3, prereg#4 | 31 | 19 | 50 | 1 | -14.57 | -24.56 | -11.71 | -17.43 | -14.57 | -14.33 | -24.27 | context_awareness | -12.06 | 47 |
| symptom course = getting worse AND intervention type = procedure/device |  | claude#7 | 28 | 13 | 41 | 1 | -12.30 | -20.74 | -8.84 | -15.76 | -12.30 | -12.37 | -20.96 | context_awareness | -10.51 | 38 |
| care setting = home/community AND intervention type = not_stated | 5.00 | gpt#8, claude#8, prereg#5 | 22 | 13 | 35 | 1 | 13.50 | 22.76 | 13.06 | 13.94 | 13.50 | 13.75 | 23.29 | context_awareness | 11.52 | 33 |

### theme:communication (n = 518; clipped means gpt 0.6132, claude 0.5911, mean 0.6021)

| rule | preregistered_id | confirmed_in | n_disc | n_conf | n_all_s2 | themes | mean_target_dev_pts | mean_target_dev_pct | gpt_target_dev_pts | claude_target_dev_pts | mean_clipped_dev_pts | mean_raw_dev_pts | mean_raw_dev_pct | worst_axis | worst_axis_term_pts | worst_axis_n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| possible trigger = not_stated AND care setting = clinic/outpatient care |  | gpt#7 | 22 | 12 | 34 | 1 | -11.02 | -18.31 | -13.38 | -8.67 | -11.02 | -12.74 | -21.30 | communication_quality | -7.59 | 24 |
| evidence basis = guideline/standard | 6.00 | gpt#1, prereg#6 | 61 | 43 | 104 | 1 | -9.25 | -15.36 | -10.84 | -7.66 | -9.25 | -9.37 | -15.67 | communication_quality | -7.63 | 75 |


## 6. Judgement

**What the subset changed at corpus level: nothing.** The S2 corpus scope confirms 2 of 10 preregistered rules, exactly as the main run did, and they are largely the same rules. `hospital/emergency care AND procedure/device` (#1) confirms on both models and in all three tables, as in the main run. `guideline/standard AND communication` (#3) confirms in the gpt and mean tables but misses the preregistered criterion on `score_rel_mean` by 0.001 (CI upper bound −0.001 against a confirmation-part mean of −0.002); the same rule with a different bootstrap seed in the mean table passes. Its confirmation is at the edge and seed-sensitive, and the report should say so rather than count it. The third confirmed corpus rule, `care setting = not_stated AND communication` (#7), is a positive slice: underspecified communication requests score 7 points above their theme and 18 points above the corpus in absolute terms. Under the null each preregistered rule confirms with probability ≈ 0.025 (same sign and one-sided CI exclusion), so 2 of 10 has P ≈ 0.025, 2 of 6 (emergency_referrals) P ≈ 0.009, 1 of 6 (communication) P ≈ 0.14. The communication drill-down is consistent with chance.

**Rows a clinician would recognise.**

1. **emergency_referrals: `episode timing = happening now/today AND care setting = hospital/emergency care`**, −14.6 points (−24.6%), n = 50, both models, worst axis context_awareness (n = 47). The user is already in or at a hospital with an acute problem, and the answer is graded on whether the model notices that and stops issuing generic "seek emergency care" advice. This is the one row that reads as a clinical insight rather than a statistical one. Caveats: 19 confirmation items, CI width about 0.2, second read.
2. **corpus: `hospital/emergency care AND procedure/device`**, −8.0 points (−16%), n = 132 across all 7 themes, both models, worst axis context_awareness. The same mechanism generalised: procedure questions set in a hospital depend on local inpatient context the model does not have. Replicates the main run (there −6.9 points on n = 160).
3. **emergency_referrals: `symptom course = getting worse AND intervention type = procedure/device`**, −12.3 points, n = 41, worst axis context_awareness. Deterioration around a procedure or device is a clinically meaningful danger zone, but the row confirms in the claude table only and was not preregistered. A lead, not a result.
4. **communication: `evidence basis = guideline/standard`**, −9.3 points (−15%), n = 104, confirmed in the gpt table and as preregistered rule #6 on `score_mean` (claude alone does not confirm), worst axis communication_quality. Users who ask for guideline-anchored answers get a more citation-shaped, less communicative reply. The same condition appears in the corpus scope here and in both runs' corpus tables, which makes it the most replicated finding of the project, but a clinician would call it a style observation, not a safety one.

**Rows that are not insights.** The two positive rules (`care setting = not_stated AND communication`, +7.3; `home/community AND intervention type = not_stated` in emergency_referrals, +13.5, n = 35) describe underspecified questions with no setting or no intervention asked for. Models do well there because the rubric for a vague question is easy to satisfy. `possible trigger = not_stated AND clinic/outpatient care` (communication, n = 34, gpt only) is too small to read. `patient age = not_stated AND stress/exertion` (#2) reversed sign on confirmation (−0.088 to +0.028), as `stress/exertion` did in the main run: that attribute value is now twice a false lead.

**Pattern worth recording.** In both theme drill-downs the preregistered rules ranked first, second and third (present in all three model tables) all failed, and the rules that confirmed were ranked fourth to sixth. Agreement across the gpt / claude / mean tables on discovery does not predict replication inside a theme at n ≈ 270–310; it mostly selects the rules with the largest winner's-curse inflation. Confirmed rules kept 79–152% of their discovery effect, non-confirmed rules mostly reversed sign.

**Bottom line.** The subset rule removed the not_applicable mass without producing new corpus-level findings. Its value is the emergency_referrals drill-down, which turns the corpus-level "hospital × procedure" row into a readable clinical statement about patients already in emergency care. That statement rests on 50 messages and a second read of the confirmation items, so it is a hypothesis for a fresh confirmation set, not a result for the paper's main table.
