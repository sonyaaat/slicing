# Subset S2 — full-data explanation tables, version 4 (corpus, no theme condition, up to 3 conditions)

Corpus run `20261017T030528Z`, subset S2 (n = 3077). No model call. Written 2026-10-19T16:20:57+00:00 (UTC).

**Version 4 = version 3 with up to 3 conditions per rule.** Theme is not a rule attribute; `th≥10` is kept. Support ≥ 40, |effect| ≥ 0.05, up to 10 rows. Rules of up to 3 conditions confirmed earlier can now enter the search unless they need theme, a form attribute or an excluded value.

**3-condition rows.** For each, the three 2-condition sub-rules are evaluated on the same items; the best one is the sub-rule with the largest deviation in the row's direction. `delta_pts` = deviation of the 3-condition rule − deviation of that sub-rule (negative on a negative row = the third condition makes it worse). `kept` = share of the sub-rule's items the third condition keeps. `rest_pts` = deviation of the sub-rule items the third condition removes. `p_within` = permutation p (10,000) of the 3-condition items against random subsets of the same size drawn from inside the sub-rule. A small `p_within` means the third attribute picks out a different group; a large one means it only narrows the sub-rule. `p_within` is computed on the same data that chose the row and is optimistic.

**These tables use all items of each scope, discovery and confirmation together.** They describe the data; they confirm nothing. `p_bh` is a permutation p (10,000) with Benjamini–Hochberg over the greedy rows of the table; it ignores that the rows were chosen on the same data, so it is optimistic. The only held-out evidence is `replicated`.

**Settings inherited from version 2.** `not_stated` is excluded from rules, together with unknown, not_applicable, parse_error, other and "none of these". On the run-4 attributes the five absence labels with the same meaning are excluded too: "no age wording", "no place named", "No action stated", "no onset-speed wording", "no explicit request". Up to 10 rows. Corpus support ≥ 40, theme support ≥ 20; |effect| ≥ 0.05 corpus, ≥ 0.08 theme. emergency_referrals also searches the 14 run-4 attributes (columns marked `r4:`), joined by prompt_id (440 of 440 items annotated).

**Columns.** One column per attribute, `*` where the rule does not constrain it. `mean_gpt` / `mean_claude` are means of the table's target family (theme-centred `score_rel_*` on corpus tables, absolute `score_*` on theme tables). `dev_pts` = (rule mean − scope mean of the table's target) × 100; `dev_pct` = deviation / scope mean of the clipped score of the table's model. `ca_gpt` / `ca_claude` = context_awareness score in the slice / scope mean, on messages with a context_awareness criterion (`ca_n` of them in the slice); theme-centred on corpus tables, absolute on theme tables, unclipped. `worst_axis` follows step 7: per model, achieved points on the axis / total positive points, theme-centred, slice minus scope, averaged over the two models; the axis with the largest term in the direction of the overall shift (`wa_pts` = that term × 100). `th≥10` = number of themes with at least 10 items in the slice.

**replicated** = the identical condition set was confirmed on a held-out split before: main run step 7 (4 rules), S2 run step 7 (corpus 3, emergency_referrals 3, communication 2), run 4 step 7 (4, emergency_referrals). A theme-scope rule is read as its conditions plus `theme = <theme>`. Same conditions, not always the same population: the main run confirmed on all 4,027 items, run 4 on all 444 emergency_referrals items.

**crowded_out rows** (below the separator) are previously confirmed rules that apply to the scope but are not in the table, with their stats on this scope and the `reason`. "eligible, not selected by greedy" means the greedy search passed them over. Any other reason means the rule could not enter this search at all. Their p is the raw permutation p (`p_perm`), not BH-adjusted.

## corpus S2 — target `score_rel_gpt`

n = 3077, scope mean -0.0014 (clipped score mean 0.4995); support ≥ 40, |effect| ≥ 0.05; 33 of 1123 patterns eligible; 10 rows, 0 replicated, 5 crowded_out.

| row | patient_age | episode_timing | possible_trigger | care_setting | symptom_course | intervention_type | evidence_basis | n | mean_gpt | mean_claude | dev_pts | dev_pct | p_bh | p_perm | ca_gpt | ca_claude | ca_n | worst_axis | wa_pts | wa_n | th≥10 | replicated | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base | * | * | * | * | * | * | * | 3077 | -0.001 | -0.003 | +0.0 | +0.0 |  |  | -0.01 / -0.01 | -0.01 / -0.01 | 2202 |  |  | 0 | 7 |  |  |
| #3 | * | * | environment food and travel | * | stable/improving | * | * | 66 | -0.081 | -0.010 | -7.9 | -15.9 | 0.0400 | 0.0127 | 0.07 / -0.01 | 0.11 / -0.01 | 53 | completeness | -3.4 | 59 | 2 | False |  |
| #1 | * | * | * | hospital/emergency care | * | * | no outside basis | 178 | -0.076 | -0.078 | -7.5 | -15.0 | 0.0020 | 0.0002 | -0.12 / -0.01 | -0.09 / -0.01 | 136 | context_awareness | -6.5 | 136 | 6 | False |  |
| #6 | * | * | * | clinic/outpatient care | * | no intervention | * | 51 | -0.075 | -0.055 | -7.4 | -14.8 | 0.0547 | 0.0438 | -0.05 / -0.01 | -0.04 / -0.01 | 44 | completeness | -7.4 | 33 | 1 | False |  |
| #10 | under 18 | * | * | * | * | * | guideline/standard | 72 | -0.054 | -0.015 | -5.2 | -10.4 | 0.0957 | 0.0957 | -0.06 / -0.01 | -0.03 / -0.01 | 57 | completeness | -3.8 | 64 | 3 | False |  |
| #7 | * | weeks months and recurring | * | * | getting worse | * | * | 117 | 0.051 | 0.065 | +5.3 | +10.6 | 0.0443 | 0.0299 | 0.03 / -0.01 | -0.02 / -0.01 | 82 | completeness | +3.1 | 96 | 6 | False |  |
| #5 | 18 to 64 | happening now/today | * | * | * | * | * | 84 | 0.061 | 0.070 | +6.2 | +12.5 | 0.0443 | 0.0310 | 0.05 / -0.01 | 0.10 / -0.01 | 50 | completeness | +9.3 | 74 | 4 | False |  |
| #2 | * | * | * | home/community | * | procedure/device | no outside basis | 160 | 0.062 | 0.015 | +6.3 | +12.6 | 0.0125 | 0.0025 | -0.05 / -0.01 | -0.06 / -0.01 | 122 | completeness | +7.3 | 148 | 6 | False |  |
| #9 | * | * | medicine/medical treatment | * | * | * | research studies | 45 | 0.068 | 0.028 | +6.9 | +13.8 | 0.0911 | 0.0820 | -0.04 / -0.01 | -0.02 / -0.01 | 32 | accuracy | +11.7 | 42 | 1 | False |  |
| #8 | * | happening now/today | injury/physical contact | * | * | procedure/device | * | 79 | 0.070 | 0.059 | +7.1 | +14.2 | 0.0400 | 0.0160 | -0.05 / -0.01 | -0.07 / -0.01 | 56 | completeness | +10.1 | 71 | 3 | False |  |
| #4 | under 18 | weeks months and recurring | * | * | * | * | no outside basis | 54 | 0.082 | 0.055 | +8.3 | +16.7 | 0.0404 | 0.0202 | -0.12 / -0.01 | -0.11 / -0.01 | 32 | instruction_following | +3.0 | 18 | 2 | False |  |
| crowded_out | * | * | * | * | * | * | guideline/standard | 104 | -0.106 | -0.074 | -10.5 | -21.0 |  | 0.0001 | 0.02 / -0.01 | 0.08 / -0.01 | 47 | communication_quality | -7.4 | 75 | 1 | True | attribute not in search (theme) |
| crowded_out | * | * | * | hospital/emergency care | * | procedure/device | * | 132 | -0.070 | -0.094 | -6.9 | -13.7 |  | 0.0023 | -0.16 / -0.01 | -0.14 / -0.01 | 91 | context_awareness | -7.4 | 91 | 4 | True | eligible, not selected by greedy |
| crowded_out | * | * | * | home/community | * | * | no outside basis | 152 | -0.050 | -0.072 | -4.9 | -9.7 |  | 0.0200 | -0.03 / -0.01 | -0.09 / -0.01 | 44 | accuracy | -5.6 | 148 | 1 | True | attribute not in search (theme); |effect| 0.049 < 0.05 |
| crowded_out | * | * | * | not_stated | * | * | * | 191 | 0.067 | 0.074 | +6.8 | +13.7 |  | 0.0002 | -0.04 / -0.01 | -0.04 / -0.01 | 63 | communication_quality | +5.3 | 174 | 1 | True | attribute not in search (theme); excluded value (not_stated) |
| crowded_out | * | * | * | not_stated | * | * | * | 161 | 0.082 | 0.090 | +8.4 | +16.7 |  | 0.0002 | -0.05 / -0.01 | -0.07 / -0.01 | 49 | communication_quality | +6.5 | 151 | 1 | True | attribute not in search (source_material, theme); excluded value (not_stated) |

**3-condition rows: best 2-condition sub-rule**

| row | rule | n | dev_pts | best sub-rule | sub_n | sub_dev_pts | third condition | delta_pts | kept | rest_pts | sub passes support/effect | p_within |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| #2 | care_setting=home/community ∧ intervention_type=procedure/device ∧ evidence_basis=no outside basis | 160 | +6.3 | care_setting=home/community ∧ intervention_type=procedure/device | 196 | +4.3 | evidence_basis=no outside basis | +2.0 | 0.82 | -4.5 | True/False | 0.0071 |
| #8 | episode_timing=happening now/today ∧ possible_trigger=injury/physical contact ∧ intervention_type=procedure/device | 79 | +7.1 | episode_timing=happening now/today ∧ possible_trigger=injury/physical contact | 180 | +4.9 | intervention_type=procedure/device | +2.2 | 0.44 | +3.3 | True/False | 0.2996 |
| #4 | patient_age=under 18 ∧ episode_timing=weeks months and recurring ∧ evidence_basis=no outside basis | 54 | +8.3 | patient_age=under 18 ∧ episode_timing=weeks months and recurring | 69 | +6.7 | evidence_basis=no outside basis | +1.7 | 0.78 | +0.7 | True/True | 0.3329 |
| crowded_out | care_setting=home/community ∧ evidence_basis=no outside basis ∧ theme=communication | 152 | -4.9 | care_setting=home/community ∧ theme=communication | 164 | -4.4 | evidence_basis=no outside basis | -0.5 | 0.93 | +1.4 | True/False | 0.4527 |
| crowded_out | care_setting=not_stated ∧ source_material=no source material ∧ theme=communication | 161 | +8.4 | care_setting=not_stated ∧ theme=communication | 191 | +6.8 | source_material=no source material | +1.5 | 0.84 | -1.3 | True/True | 0.1086 |

Replication sources: crowded_out evidence_basis=guideline/standard AND theme=communication ← S2 step 7 communication; S2 step 7 corpus; main step 7; crowded_out care_setting=hospital/emergency care AND intervention_type=procedure/device ← S2 step 7 corpus; main step 7; crowded_out care_setting=home/community AND evidence_basis=no outside basis AND theme=communication ← main step 7; crowded_out care_setting=not_stated AND theme=communication ← S2 step 7 corpus; crowded_out care_setting=not_stated AND source_material=no source material AND theme=communication ← main step 7

## corpus S2 — target `score_rel_claude`

n = 3077, scope mean -0.0031 (clipped score mean 0.4890); support ≥ 40, |effect| ≥ 0.05; 35 of 1123 patterns eligible; 10 rows, 1 replicated, 4 crowded_out.

| row | patient_age | episode_timing | possible_trigger | care_setting | symptom_course | intervention_type | evidence_basis | n | mean_gpt | mean_claude | dev_pts | dev_pct | p_bh | p_perm | ca_gpt | ca_claude | ca_n | worst_axis | wa_pts | wa_n | th≥10 | replicated | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base | * | * | * | * | * | * | * | 3077 | -0.001 | -0.003 | +0.0 | +0.0 |  |  | -0.01 / -0.01 | -0.01 / -0.01 | 2202 |  |  | 0 | 7 |  |  |
| #1 | * | * | * | hospital/emergency care | getting worse | * | * | 40 | -0.116 | -0.174 | -17.1 | -35.0 | 0.0005 | 0.0001 | -0.00 / -0.01 | -0.17 / -0.01 | 35 | context_awareness | -10.5 | 35 | 1 | False |  |
| #6 | * | * | * | hospital/emergency care | * | procedure/device | * | 132 | -0.070 | -0.094 | -9.1 | -18.5 | 0.0005 | 0.0001 | -0.16 / -0.01 | -0.14 / -0.01 | 91 | context_awareness | -7.4 | 91 | 4 | True |  |
| #7 | * | * | stress/exertion | home/community | * | * | * | 85 | -0.025 | -0.057 | -5.4 | -11.1 | 0.0786 | 0.0629 | -0.06 / -0.01 | -0.09 / -0.01 | 66 | accuracy | -5.5 | 71 | 4 | False |  |
| #5 | * | happening now/today | injury/physical contact | * | * | procedure/device | * | 79 | 0.070 | 0.059 | +6.2 | +12.8 | 0.0554 | 0.0388 | -0.05 / -0.01 | -0.07 / -0.01 | 56 | completeness | +10.1 | 71 | 3 | False |  |
| #9 | * | happening now/today | * | * | stable/improving | behavior/self-care | * | 48 | 0.021 | 0.061 | +6.4 | +13.0 | 0.0982 | 0.0982 | 0.05 / -0.01 | 0.02 / -0.01 | 36 | completeness | +6.2 | 43 | 1 | False |  |
| #10 | 18 to 64 | weeks months and recurring | * | * | stable/improving | * | * | 48 | 0.025 | 0.064 | +6.7 | +13.7 | 0.0887 | 0.0798 | 0.06 / -0.01 | 0.10 / -0.01 | 30 | accuracy | +5.2 | 43 | 1 | False |  |
| #4 | * | weeks months and recurring | * | * | getting worse | * | no outside basis | 96 | 0.051 | 0.065 | +6.9 | +14.0 | 0.0253 | 0.0132 | 0.04 / -0.01 | -0.03 / -0.01 | 72 | completeness | +3.6 | 79 | 5 | False |  |
| #3 | 18 to 64 | happening now/today | * | * | * | * | * | 84 | 0.061 | 0.070 | +7.3 | +14.9 | 0.0253 | 0.0139 | 0.05 / -0.01 | 0.10 / -0.01 | 50 | completeness | +9.3 | 74 | 4 | False |  |
| #8 | * | weeks months and recurring | injury/physical contact | * | * | * | * | 46 | 0.022 | 0.092 | +9.5 | +19.5 | 0.0253 | 0.0152 | 0.14 / -0.01 | 0.28 / -0.01 | 30 | accuracy | +2.3 | 41 | 1 | False |  |
| #2 | * | weeks months and recurring | * | * | * | * | guideline/standard | 63 | 0.025 | 0.094 | +9.7 | +19.9 | 0.0133 | 0.0040 | -0.01 / -0.01 | 0.01 / -0.01 | 45 | completeness | +3.4 | 52 | 4 | False |  |
| crowded_out | * | * | * | * | * | * | guideline/standard | 104 | -0.106 | -0.074 | -7.1 | -14.4 |  | 0.0058 | 0.02 / -0.01 | 0.08 / -0.01 | 47 | communication_quality | -7.4 | 75 | 1 | True | attribute not in search (theme) |
| crowded_out | * | * | * | home/community | * | * | no outside basis | 152 | -0.050 | -0.072 | -6.9 | -14.0 |  | 0.0014 | -0.03 / -0.01 | -0.09 / -0.01 | 44 | accuracy | -5.6 | 148 | 1 | True | attribute not in search (theme) |
| crowded_out | * | * | * | not_stated | * | * | * | 191 | 0.067 | 0.074 | +7.7 | +15.8 |  | 0.0002 | -0.04 / -0.01 | -0.04 / -0.01 | 63 | communication_quality | +5.3 | 174 | 1 | True | attribute not in search (theme); excluded value (not_stated) |
| crowded_out | * | * | * | not_stated | * | * | * | 161 | 0.082 | 0.090 | +9.3 | +19.1 |  | 0.0001 | -0.05 / -0.01 | -0.07 / -0.01 | 49 | communication_quality | +6.5 | 151 | 1 | True | attribute not in search (source_material, theme); excluded value (not_stated) |

**3-condition rows: best 2-condition sub-rule**

| row | rule | n | dev_pts | best sub-rule | sub_n | sub_dev_pts | third condition | delta_pts | kept | rest_pts | sub passes support/effect | p_within |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| #5 | episode_timing=happening now/today ∧ possible_trigger=injury/physical contact ∧ intervention_type=procedure/device | 79 | +6.2 | episode_timing=happening now/today ∧ possible_trigger=injury/physical contact | 180 | +4.4 | intervention_type=procedure/device | +1.8 | 0.44 | +3.0 | True/False | 0.4114 |
| #9 | episode_timing=happening now/today ∧ symptom_course=stable/improving ∧ intervention_type=behavior/self-care | 48 | +6.4 | symptom_course=stable/improving ∧ intervention_type=behavior/self-care | 128 | +4.2 | episode_timing=happening now/today | +2.1 | 0.38 | +3.0 | True/False | 0.4425 |
| #10 | patient_age=18 to 64 ∧ episode_timing=weeks months and recurring ∧ symptom_course=stable/improving | 48 | +6.7 | episode_timing=weeks months and recurring ∧ symptom_course=stable/improving | 312 | +3.3 | patient_age=18 to 64 | +3.4 | 0.15 | +2.7 | True/False | 0.3383 |
| #4 | episode_timing=weeks months and recurring ∧ symptom_course=getting worse ∧ evidence_basis=no outside basis | 96 | +6.9 | episode_timing=weeks months and recurring ∧ symptom_course=getting worse | 117 | +6.8 | evidence_basis=no outside basis | +0.0 | 0.82 | +6.7 | True/True | 0.9791 |
| crowded_out | care_setting=home/community ∧ evidence_basis=no outside basis ∧ theme=communication | 152 | -6.9 | care_setting=home/community ∧ theme=communication | 164 | -5.9 | evidence_basis=no outside basis | -0.9 | 0.93 | +6.1 | True/True | 0.1313 |
| crowded_out | care_setting=not_stated ∧ source_material=no source material ∧ theme=communication | 161 | +9.3 | care_setting=not_stated ∧ theme=communication | 191 | +7.7 | source_material=no source material | +1.6 | 0.84 | -0.9 | True/True | 0.0991 |

Replication sources: #6 ← S2 step 7 corpus; main step 7; crowded_out evidence_basis=guideline/standard AND theme=communication ← S2 step 7 communication; S2 step 7 corpus; main step 7; crowded_out care_setting=home/community AND evidence_basis=no outside basis AND theme=communication ← main step 7; crowded_out care_setting=not_stated AND theme=communication ← S2 step 7 corpus; crowded_out care_setting=not_stated AND source_material=no source material AND theme=communication ← main step 7

## corpus S2 — target `score_rel_mean`

n = 3077, scope mean -0.0023 (clipped score mean 0.4943); support ≥ 40, |effect| ≥ 0.05; 31 of 1123 patterns eligible; 10 rows, 0 replicated, 5 crowded_out.

| row | patient_age | episode_timing | possible_trigger | care_setting | symptom_course | intervention_type | evidence_basis | n | mean_gpt | mean_claude | dev_pts | dev_pct | p_bh | p_perm | ca_gpt | ca_claude | ca_n | worst_axis | wa_pts | wa_n | th≥10 | replicated | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base | * | * | * | * | * | * | * | 3077 | -0.001 | -0.003 | +0.0 | +0.0 |  |  | -0.01 / -0.01 | -0.01 / -0.01 | 2202 |  |  | 0 | 7 |  |  |
| #5 | * | * | * | hospital/emergency care | getting worse | * | * | 40 | -0.116 | -0.174 | -14.3 | -28.9 | 0.0010 | 0.0002 | -0.00 / -0.01 | -0.17 / -0.01 | 35 | context_awareness | -10.5 | 35 | 1 | False |  |
| #1 | * | * | * | hospital/emergency care | * | * | no outside basis | 178 | -0.076 | -0.078 | -7.5 | -15.2 | 0.0010 | 0.0001 | -0.12 / -0.01 | -0.09 / -0.01 | 136 | context_awareness | -6.5 | 136 | 6 | False |  |
| #8 | * | * | environment food and travel | home/community | * | medicine/supplement | * | 46 | -0.060 | -0.071 | -6.3 | -12.8 | 0.0762 | 0.0762 | 0.11 / -0.01 | 0.14 / -0.01 | 36 | accuracy | -3.5 | 42 | 2 | False |  |
| #7 | * | * | * | clinic/outpatient care | * | no intervention | * | 51 | -0.075 | -0.055 | -6.3 | -12.7 | 0.0762 | 0.0682 | -0.05 / -0.01 | -0.04 / -0.01 | 44 | completeness | -7.4 | 33 | 1 | False |  |
| #9 | * | happening now/today | stress/exertion | * | * | * | * | 55 | -0.047 | -0.075 | -5.9 | -12.0 | 0.0762 | 0.0690 | -0.07 / -0.01 | -0.10 / -0.01 | 40 | accuracy | -5.8 | 42 | 3 | False |  |
| #3 | * | weeks months and recurring | * | * | getting worse | * | * | 117 | 0.051 | 0.065 | +6.0 | +12.2 | 0.0223 | 0.0067 | 0.03 / -0.01 | -0.02 / -0.01 | 82 | completeness | +3.1 | 96 | 6 | False |  |
| #2 | * | happening now/today | injury/physical contact | * | * | procedure/device | * | 79 | 0.070 | 0.059 | +6.7 | +13.5 | 0.0265 | 0.0145 | -0.05 / -0.01 | -0.07 / -0.01 | 56 | completeness | +10.1 | 71 | 3 | False |  |
| #4 | 18 to 64 | happening now/today | * | * | * | * | * | 84 | 0.061 | 0.070 | +6.7 | +13.7 | 0.0255 | 0.0102 | 0.05 / -0.01 | 0.10 / -0.01 | 50 | completeness | +9.3 | 74 | 4 | False |  |
| #6 | under 18 | weeks months and recurring | * | * | * | * | * | 69 | 0.065 | 0.070 | +7.0 | +14.2 | 0.0265 | 0.0159 | -0.15 / -0.01 | -0.11 / -0.01 | 45 | completeness | +3.4 | 59 | 3 | False |  |
| #10 | * | * | injury/physical contact | home/community | stable/improving | * | * | 44 | 0.052 | 0.086 | +7.1 | +14.4 | 0.0697 | 0.0488 | 0.04 / -0.01 | 0.11 / -0.01 | 28 | completeness | +9.0 | 42 | 1 | False |  |
| crowded_out | * | * | * | * | * | * | guideline/standard | 104 | -0.106 | -0.074 | -8.8 | -17.7 |  | 0.0002 | 0.02 / -0.01 | 0.08 / -0.01 | 47 | communication_quality | -7.4 | 75 | 1 | True | attribute not in search (theme) |
| crowded_out | * | * | * | hospital/emergency care | * | procedure/device | * | 132 | -0.070 | -0.094 | -8.0 | -16.1 |  | 0.0002 | -0.16 / -0.01 | -0.14 / -0.01 | 91 | context_awareness | -7.4 | 91 | 4 | True | eligible, not selected by greedy |
| crowded_out | * | * | * | home/community | * | * | no outside basis | 152 | -0.050 | -0.072 | -5.9 | -11.9 |  | 0.0028 | -0.03 / -0.01 | -0.09 / -0.01 | 44 | accuracy | -5.6 | 148 | 1 | True | attribute not in search (theme) |
| crowded_out | * | * | * | not_stated | * | * | * | 191 | 0.067 | 0.074 | +7.3 | +14.7 |  | 0.0001 | -0.04 / -0.01 | -0.04 / -0.01 | 63 | communication_quality | +5.3 | 174 | 1 | True | attribute not in search (theme); excluded value (not_stated) |
| crowded_out | * | * | * | not_stated | * | * | * | 161 | 0.082 | 0.090 | +8.9 | +17.9 |  | 0.0001 | -0.05 / -0.01 | -0.07 / -0.01 | 49 | communication_quality | +6.5 | 151 | 1 | True | attribute not in search (source_material, theme); excluded value (not_stated) |

**3-condition rows: best 2-condition sub-rule**

| row | rule | n | dev_pts | best sub-rule | sub_n | sub_dev_pts | third condition | delta_pts | kept | rest_pts | sub passes support/effect | p_within |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| #8 | possible_trigger=environment food and travel ∧ care_setting=home/community ∧ intervention_type=medicine/supplement | 46 | -6.3 | possible_trigger=environment food and travel ∧ care_setting=home/community | 160 | -2.5 | intervention_type=medicine/supplement | -3.8 | 0.29 | -0.9 | True/False | 0.1595 |
| #2 | episode_timing=happening now/today ∧ possible_trigger=injury/physical contact ∧ intervention_type=procedure/device | 79 | +6.7 | episode_timing=happening now/today ∧ possible_trigger=injury/physical contact | 180 | +4.7 | intervention_type=procedure/device | +2.0 | 0.44 | +3.2 | True/False | 0.3150 |
| #10 | possible_trigger=injury/physical contact ∧ care_setting=home/community ∧ symptom_course=stable/improving | 44 | +7.1 | possible_trigger=injury/physical contact ∧ symptom_course=stable/improving | 73 | +5.1 | care_setting=home/community | +2.1 | 0.60 | +1.9 | True/True | 0.3434 |
| crowded_out | care_setting=home/community ∧ evidence_basis=no outside basis ∧ theme=communication | 152 | -5.9 | care_setting=home/community ∧ theme=communication | 164 | -5.2 | evidence_basis=no outside basis | -0.7 | 0.93 | +3.7 | True/True | 0.2190 |
| crowded_out | care_setting=not_stated ∧ source_material=no source material ∧ theme=communication | 161 | +8.9 | care_setting=not_stated ∧ theme=communication | 191 | +7.3 | source_material=no source material | +1.6 | 0.84 | -1.1 | True/True | 0.0899 |

Replication sources: crowded_out evidence_basis=guideline/standard AND theme=communication ← S2 step 7 communication; S2 step 7 corpus; main step 7; crowded_out care_setting=hospital/emergency care AND intervention_type=procedure/device ← S2 step 7 corpus; main step 7; crowded_out care_setting=home/community AND evidence_basis=no outside basis AND theme=communication ← main step 7; crowded_out care_setting=not_stated AND theme=communication ← S2 step 7 corpus; crowded_out care_setting=not_stated AND source_material=no source material AND theme=communication ← main step 7

## Reading

- **Allowing a third condition does not change the negative side.** The strongest rows are the same 2-condition hospital rules as in v3: hospital × getting worse (−17.1 Claude, −14.3 mean, n = 40), hospital × no outside basis (−7.5, n = 178) and hospital × procedure/device (−9.1 Claude, replicated). The search had 1,123 candidate patterns instead of 208, and no 3-condition rule beat them.
- **3-condition rows: 10 across the three tables, 7 distinct rules, and 9 of the 10 are positive.** The only negative one is environment/food/travel × home/community × medicine/supplement (mean, −6.3, n = 46). Its best sub-rule sits at −2.5, so the third condition adds −3.8 points. But p_within = 0.16, so the third condition only narrows the sub-rule to 29% of its items. It does not pick out a different group.
- **The third condition matters in one row only.** That row is GPT #2, home/community × procedure/device × no outside basis (+6.3, n = 160). The sub-rule is +4.3, the third condition keeps 82% of its items, and the 36 items it removes sit at −4.5. Here p_within = 0.007, so asking for guidelines or research inside home procedure questions is what pulls the group down. That is consistent with the replicated guideline/standard effect in communication.
- **Everywhere else the third attribute narrows rather than explains.** p_within ranges from 0.30 to 0.98 and delta_pts from +0.0 to +3.4. In 7 of the 10 rows the best sub-rule misses the 0.05 effect threshold on its own. The third condition mostly pushes a weak sub-rule over the threshold by keeping 15 to 60% of its items, which is the selection effect a deeper search is expected to produce.
- **For the paper, two conditions are enough on this corpus.** The 3-condition rows add no replicated finding and one weak lead.
