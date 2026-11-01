# Subset S2 — full-data explanation tables

Corpus run `20261017T030528Z`, subset S2 (n = 3077). No model call. Written 2026-10-19T15:48:57+00:00 (UTC).

**These tables use all items of each scope, discovery and confirmation together.** They describe the data; they confirm nothing. `p_bh` is a permutation p (10,000) with Benjamini–Hochberg over the rows of the table, and it ignores that the rows were chosen on the same data, so it is optimistic. The only held-out evidence is `replicated`.

**Columns.** One column per attribute (and theme on corpus tables), `*` where the rule does not constrain it. `mean_gpt` / `mean_claude` are means of the table's target family (theme-centred `score_rel_*` on corpus tables, absolute `score_*` on theme tables). `dev_pts` = (rule mean − scope mean of the table's target) × 100. `dev_pct` = deviation / scope mean of the clipped score of the table's model. Row 0 is the scope baseline. Rows are sorted worst first; `step` is the greedy order.

**replicated** = the identical condition set was confirmed on a held-out split in an earlier check: main run step 7 (4 confirmed rules), S2 run step 7 (8), run 4 step 7 (4). A theme-scope rule is read as its conditions plus `theme = <theme>`. Run 4 used its own attribute vocabulary (prompt_form, severity_wording, …), which shares no attribute with the universal set, so no run-4 rule can match. The main run confirmed on all 4,027 items, the S2 run on S2 only; a match means the same conditions, not the same population.

## corpus S2 — target `score_rel_gpt`

n = 3077, scope mean -0.0014 (clipped score mean 0.4995); support ≥ 60, |effect| ≥ 0.05; 26 of 533 patterns eligible; 8 rows, 2 replicated.

| step | patient_age | episode_timing | possible_trigger | care_setting | symptom_course | intervention_type | evidence_basis | theme | n | mean_gpt | mean_claude | dev_pts | dev_pct | p_bh | replicated |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | * | * | * | * | * | * | * | * | 3077 | -0.001 | -0.003 | +0.0 | +0.0 |  |  |
| 1 | * | * | * | * | * | * | guideline/standard | communication | 104 | -0.106 | -0.074 | -10.5 | -21.0 | 0.0004 | True |
| 5 | * | * | environment food and travel | * | stable/improving | * | * | * | 66 | -0.081 | -0.010 | -7.9 | -15.9 | 0.0188 | False |
| 6 | not_stated | * | * | * | * | * | * | complex_responses | 82 | -0.078 | -0.084 | -7.6 | -15.3 | 0.0112 | False |
| 3 | * | * | * | hospital/emergency care | * | * | no outside basis | * | 178 | -0.076 | -0.078 | -7.5 | -15.0 | 0.0004 | False |
| 4 | * | not_stated | * | * | * | not_stated | * | * | 77 | -0.072 | -0.056 | -7.0 | -14.0 | 0.0225 | False |
| 8 | 18 to 64 | happening now/today | * | * | * | * | * | * | 84 | 0.061 | 0.070 | +6.2 | +12.5 | 0.0290 | False |
| 2 | * | * | * | not_stated | * | * | * | communication | 191 | 0.067 | 0.074 | +6.8 | +13.7 | 0.0013 | True |
| 7 | * | * | * | not_stated | getting worse | * | * | * | 101 | 0.079 | 0.071 | +8.1 | +16.2 | 0.0046 | False |

Replicated rows: step 1 ← S2 step 7 (S2 communication); S2 step 7 (S2 corpus); main step 7 (corpus); step 2 ← S2 step 7 (S2 corpus)

## corpus S2 — target `score_rel_claude`

n = 3077, scope mean -0.0031 (clipped score mean 0.4890); support ≥ 60, |effect| ≥ 0.05; 27 of 533 patterns eligible; 8 rows, 2 replicated.

| step | patient_age | episode_timing | possible_trigger | care_setting | symptom_course | intervention_type | evidence_basis | theme | n | mean_gpt | mean_claude | dev_pts | dev_pct | p_bh | replicated |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | * | * | * | * | * | * | * | * | 3077 | -0.001 | -0.003 | +0.0 | +0.0 |  |  |
| 1 | * | * | not_stated | hospital/emergency care | * | * | * | * | 125 | -0.090 | -0.100 | -9.7 | -19.7 | 0.0004 | False |
| 3 | * | * | * | * | * | * | guideline/standard | communication | 104 | -0.106 | -0.074 | -7.1 | -14.4 | 0.0096 | True |
| 7 | * | * | * | home/community | * | * | * | communication | 164 | -0.046 | -0.062 | -5.9 | -12.1 | 0.0085 | False |
| 8 | * | * | injury/physical contact | home/community | * | * | * | * | 158 | 0.020 | 0.047 | +5.0 | +10.2 | 0.0171 | False |
| 6 | 18 to 64 | happening now/today | * | * | * | * | * | * | 84 | 0.061 | 0.070 | +7.3 | +14.9 | 0.0113 | False |
| 5 | * | * | * | * | * | not_stated | * | emergency_referrals | 92 | 0.045 | 0.074 | +7.7 | +15.7 | 0.0085 | False |
| 2 | * | * | * | not_stated | * | * | * | communication | 191 | 0.067 | 0.074 | +7.7 | +15.8 | 0.0004 | True |
| 4 | * | weeks months and recurring | * | * | * | * | guideline/standard | * | 63 | 0.025 | 0.094 | +9.7 | +19.9 | 0.0085 | False |

Replicated rows: step 3 ← S2 step 7 (S2 communication); S2 step 7 (S2 corpus); main step 7 (corpus); step 2 ← S2 step 7 (S2 corpus)

## corpus S2 — target `score_rel_mean`

n = 3077, scope mean -0.0023 (clipped score mean 0.4943); support ≥ 60, |effect| ≥ 0.05; 24 of 533 patterns eligible; 8 rows, 2 replicated.

| step | patient_age | episode_timing | possible_trigger | care_setting | symptom_course | intervention_type | evidence_basis | theme | n | mean_gpt | mean_claude | dev_pts | dev_pct | p_bh | replicated |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | * | * | * | * | * | * | * | * | 3077 | -0.001 | -0.003 | +0.0 | +0.0 |  |  |
| 1 | * | * | not_stated | hospital/emergency care | * | * | * | * | 125 | -0.090 | -0.100 | -9.3 | -18.7 | 0.0004 | False |
| 3 | * | * | * | * | * | * | guideline/standard | communication | 104 | -0.106 | -0.074 | -8.8 | -17.7 | 0.0004 | True |
| 7 | not_stated | * | * | * | * | * | * | complex_responses | 82 | -0.078 | -0.084 | -7.8 | -15.9 | 0.0059 | False |
| 5 | * | * | * | home/community | * | * | * | emergency_referrals | 181 | 0.046 | 0.050 | +5.0 | +10.2 | 0.0069 | False |
| 4 | 18 to 64 | happening now/today | * | * | * | * | * | * | 84 | 0.061 | 0.070 | +6.7 | +13.7 | 0.0107 | False |
| 2 | * | * | * | not_stated | * | * | * | communication | 191 | 0.067 | 0.074 | +7.3 | +14.7 | 0.0005 | True |
| 6 | * | * | * | not_stated | getting worse | * | * | * | 101 | 0.079 | 0.071 | +7.7 | +15.6 | 0.0024 | False |
| 8 | * | * | * | * | * | * | guideline/standard | hedging | 60 | 0.080 | 0.073 | +7.9 | +16.0 | 0.0107 | False |

Replicated rows: step 3 ← S2 step 7 (S2 communication); S2 step 7 (S2 corpus); main step 7 (corpus); step 2 ← S2 step 7 (S2 corpus)

## theme emergency_referrals — target `score_gpt`

n = 440, scope mean 0.5963 (clipped score mean 0.5963); support ≥ 20, |effect| ≥ 0.08; 27 of 287 patterns eligible; 8 rows, 2 replicated.

| step | patient_age | episode_timing | possible_trigger | care_setting | symptom_course | intervention_type | evidence_basis | n | mean_gpt | mean_claude | dev_pts | dev_pct | p_bh | replicated |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | * | * | * | * | * | * | * | 440 | 0.596 | 0.590 | +0.0 | +0.0 |  |  |
| 5 | * | * | * | clinic/outpatient care | * | * | no outside basis | 20 | 0.448 | 0.517 | -14.8 | -24.8 | 0.0311 | False |
| 1 | * | happening now/today | * | hospital/emergency care | * | * | * | 50 | 0.479 | 0.416 | -11.7 | -19.6 | 0.0205 | True |
| 8 | * | not_stated | not_stated | * | * | * | * | 27 | 0.499 | 0.534 | -9.8 | -16.4 | 0.0838 | False |
| 3 | * | * | not_stated | * | stable/improving | * | * | 52 | 0.701 | 0.659 | +10.4 | +17.5 | 0.0205 | False |
| 7 | * | happening now/today | * | * | * | not_stated | * | 41 | 0.703 | 0.725 | +10.6 | +17.8 | 0.0294 | False |
| 6 | * | * | injury/physical contact | home/community | * | * | * | 29 | 0.705 | 0.682 | +10.9 | +18.3 | 0.0448 | False |
| 2 | * | happening now/today | medicine/medical treatment | * | * | * | * | 28 | 0.725 | 0.716 | +12.9 | +21.6 | 0.0294 | False |
| 4 | * | * | * | home/community | * | not_stated | * | 35 | 0.727 | 0.729 | +13.1 | +21.9 | 0.0205 | True |

Replicated rows: step 1 ← S2 step 7 (S2 emergency_referrals); step 4 ← S2 step 7 (S2 emergency_referrals)

## theme emergency_referrals — target `score_claude`

n = 440, scope mean 0.5898 (clipped score mean 0.5898); support ≥ 20, |effect| ≥ 0.08; 26 of 287 patterns eligible; 8 rows, 0 replicated.

| step | patient_age | episode_timing | possible_trigger | care_setting | symptom_course | intervention_type | evidence_basis | n | mean_gpt | mean_claude | dev_pts | dev_pct | p_bh | replicated |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | * | * | * | * | * | * | * | 440 | 0.596 | 0.590 | +0.0 | +0.0 |  |  |
| 1 | * | * | * | hospital/emergency care | getting worse | * | * | 29 | 0.446 | 0.341 | -24.8 | -42.1 | 0.0008 | False |
| 4 | * | * | stress/exertion | * | * | * | * | 21 | 0.472 | 0.430 | -16.0 | -27.1 | 0.0264 | False |
| 5 | * | * | not_stated | * | * | procedure/device | * | 56 | 0.577 | 0.467 | -12.3 | -20.8 | 0.0044 | False |
| 8 | * | * | injury/physical contact | home/community | * | * | * | 29 | 0.705 | 0.682 | +9.2 | +15.6 | 0.0989 | False |
| 6 | * | happening now/today | * | * | * | behavior/self-care | * | 25 | 0.663 | 0.700 | +11.0 | +18.7 | 0.0808 | False |
| 7 | * | weeks months and recurring | * | * | * | not_stated | * | 26 | 0.697 | 0.706 | +11.6 | +19.7 | 0.0648 | False |
| 2 | * | happening now/today | medicine/medical treatment | * | * | * | * | 28 | 0.725 | 0.716 | +12.6 | +21.4 | 0.0414 | False |
| 3 | * | happening now/today | * | * | * | not_stated | * | 41 | 0.703 | 0.725 | +13.5 | +22.9 | 0.0077 | False |

## theme emergency_referrals — target `score_mean`

n = 440, scope mean 0.5931 (clipped score mean 0.5931); support ≥ 20, |effect| ≥ 0.08; 25 of 287 patterns eligible; 8 rows, 1 replicated.

| step | patient_age | episode_timing | possible_trigger | care_setting | symptom_course | intervention_type | evidence_basis | n | mean_gpt | mean_claude | dev_pts | dev_pct | p_bh | replicated |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | * | * | * | * | * | * | * | 440 | 0.596 | 0.590 | +0.0 | +0.0 |  |  |
| 1 | * | * | * | hospital/emergency care | getting worse | * | * | 29 | 0.446 | 0.341 | -20.0 | -33.7 | 0.0024 | False |
| 4 | * | * | stress/exertion | * | * | * | * | 21 | 0.472 | 0.430 | -14.2 | -24.0 | 0.0281 | False |
| 8 | * | * | * | clinic/outpatient care | * | * | no outside basis | 20 | 0.448 | 0.517 | -11.1 | -18.6 | 0.0806 | False |
| 5 | * | * | not_stated | * | stable/improving | * | * | 52 | 0.701 | 0.659 | +8.7 | +14.7 | 0.0281 | False |
| 6 | * | * | injury/physical contact | home/community | * | * | * | 29 | 0.705 | 0.682 | +10.1 | +17.0 | 0.0554 | False |
| 7 | * | happening now/today | * | * | * | not_stated | * | 41 | 0.703 | 0.725 | +12.1 | +20.4 | 0.0163 | False |
| 2 | * | happening now/today | medicine/medical treatment | * | * | * | * | 28 | 0.725 | 0.716 | +12.7 | +21.5 | 0.0281 | False |
| 3 | * | * | * | home/community | * | not_stated | * | 35 | 0.727 | 0.729 | +13.5 | +22.8 | 0.0128 | True |

Replicated rows: step 3 ← S2 step 7 (S2 emergency_referrals)

## theme communication — target `score_gpt`

n = 518, scope mean 0.6132 (clipped score mean 0.6132); support ≥ 20, |effect| ≥ 0.08; 31 of 312 patterns eligible; 8 rows, 1 replicated.

| step | patient_age | episode_timing | possible_trigger | care_setting | symptom_course | intervention_type | evidence_basis | n | mean_gpt | mean_claude | dev_pts | dev_pct | p_bh | replicated |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | * | * | * | * | * | * | * | 518 | 0.613 | 0.591 | +0.0 | +0.0 |  |  |
| 4 | * | * | * | * | not_stated | not_stated | * | 35 | 0.501 | 0.526 | -11.2 | -18.2 | 0.0354 | False |
| 1 | * | * | * | * | * | * | guideline/standard | 104 | 0.505 | 0.515 | -10.8 | -17.7 | 0.0008 | True |
| 2 | * | happening now/today | * | home/community | * | * | * | 71 | 0.532 | 0.492 | -8.2 | -13.3 | 0.0272 | False |
| 8 | * | * | * | home/community | * | procedure/device | * | 21 | 0.701 | 0.655 | +8.8 | +14.3 | 0.1731 | False |
| 6 | * | * | * | not_stated | * | medicine/supplement | * | 42 | 0.709 | 0.679 | +9.5 | +15.6 | 0.0473 | False |
| 3 | * | * | * | * | not_stated | no intervention | * | 50 | 0.728 | 0.702 | +11.5 | +18.8 | 0.0112 | False |
| 7 | under 18 | * | * | not_stated | * | * | * | 21 | 0.739 | 0.657 | +12.6 | +20.5 | 0.0587 | False |
| 5 | * | * | * | * | getting worse | * | no outside basis | 34 | 0.751 | 0.702 | +13.8 | +22.5 | 0.0112 | False |

Replicated rows: step 1 ← S2 step 7 (S2 communication); S2 step 7 (S2 corpus); main step 7 (corpus)

## theme communication — target `score_claude`

n = 518, scope mean 0.5911 (clipped score mean 0.5911); support ≥ 20, |effect| ≥ 0.08; 32 of 312 patterns eligible; 8 rows, 0 replicated.

| step | patient_age | episode_timing | possible_trigger | care_setting | symptom_course | intervention_type | evidence_basis | n | mean_gpt | mean_claude | dev_pts | dev_pct | p_bh | replicated |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | * | * | * | * | * | * | * | 518 | 0.613 | 0.591 | +0.0 | +0.0 |  |  |
| 6 | * | * | environment food and travel | home/community | * | * | * | 22 | 0.527 | 0.440 | -15.1 | -25.5 | 0.0374 | False |
| 7 | * | * | * | clinic/outpatient care | * | medicine/supplement | * | 21 | 0.424 | 0.442 | -14.9 | -25.3 | 0.0374 | False |
| 8 | * | * | * | hospital/emergency care | not_stated | * | * | 22 | 0.539 | 0.456 | -13.5 | -22.9 | 0.0470 | False |
| 3 | * | happening now/today | * | home/community | * | * | * | 71 | 0.532 | 0.492 | -9.9 | -16.8 | 0.0128 | False |
| 5 | * | weeks months and recurring | * | * | * | no intervention | * | 28 | 0.569 | 0.499 | -9.2 | -15.6 | 0.1041 | False |
| 1 | * | * | * | not_stated | * | * | no outside basis | 142 | 0.687 | 0.681 | +9.0 | +15.2 | 0.0008 | False |
| 2 | * | * | * | * | not_stated | no intervention | * | 50 | 0.728 | 0.702 | +11.0 | +18.7 | 0.0187 | False |
| 4 | * | * | * | * | getting worse | * | no outside basis | 34 | 0.751 | 0.702 | +11.1 | +18.7 | 0.0427 | False |

## theme communication — target `score_mean`

n = 518, scope mean 0.6021 (clipped score mean 0.6021); support ≥ 20, |effect| ≥ 0.08; 32 of 312 patterns eligible; 8 rows, 1 replicated.

| step | patient_age | episode_timing | possible_trigger | care_setting | symptom_course | intervention_type | evidence_basis | n | mean_gpt | mean_claude | dev_pts | dev_pct | p_bh | replicated |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | * | * | * | * | * | * | * | 518 | 0.613 | 0.591 | +0.0 | +0.0 |  |  |
| 8 | * | * | environment food and travel | home/community | * | * | * | 22 | 0.527 | 0.440 | -11.9 | -19.7 | 0.0574 | False |
| 5 | * | * | * | * | * | * | guideline/standard | 104 | 0.505 | 0.515 | -9.2 | -15.4 | 0.0012 | True |
| 4 | * | happening now/today | * | home/community | * | * | * | 71 | 0.532 | 0.492 | -9.0 | -15.0 | 0.0098 | False |
| 7 | * | * | * | * | not_stated | not_stated | * | 35 | 0.501 | 0.526 | -8.9 | -14.7 | 0.0605 | False |
| 1 | * | * | * | not_stated | * | * | no outside basis | 142 | 0.687 | 0.681 | +8.2 | +13.6 | 0.0012 | False |
| 6 | * | * | * | not_stated | * | medicine/supplement | * | 42 | 0.709 | 0.679 | +9.2 | +15.3 | 0.0479 | False |
| 2 | * | * | * | * | not_stated | no intervention | * | 50 | 0.728 | 0.702 | +11.3 | +18.7 | 0.0080 | False |
| 3 | * | * | * | * | getting worse | * | no outside basis | 34 | 0.751 | 0.702 | +12.4 | +20.6 | 0.0134 | False |

Replicated rows: step 5 ← S2 step 7 (S2 communication); S2 step 7 (S2 corpus); main step 7 (corpus)

## Reading

- **Replicated rows are few: 4 distinct rules across 9 tables.** `evidence basis = guideline/standard` in communication (−9 to −11 points, n = 104) appears in five tables and was confirmed three times before. `care setting = not_stated` in communication (+7 points, n = 191) appears in three corpus tables. In emergency_referrals, `happening now/today AND hospital/emergency care` (−11.7 points on GPT, n = 50) and `home/community AND intervention type = not_stated` (+13 points, n = 35) appear only in the GPT and mean tables.
- **The twice-confirmed `hospital/emergency care AND procedure/device` is absent, but only because the greedy search crowded it out.** On all S2 items it still holds at −8.0 points (n = 132). The overlapping rule `possible trigger = not_stated AND hospital/emergency care` (−9.3, n = 125, 65 items shared) took its place in the claude and mean tables. Both describe the hospital-setting slice. A full-data table is not a list of everything that holds.
- **The largest effect is new and unreplicated.** In emergency_referrals, `hospital/emergency care AND symptom course = getting worse` sits at −24.8 points on Claude and −20.0 on the mean, n = 29. Claude is at 0.34 and GPT at 0.45. It is the same hospital-context pattern, sharpened, but n = 29 and no held-out test.
- `possible trigger = stress/exertion` reappears in emergency_referrals (−16 on Claude, n = 21). It reversed sign on held-out data twice before, so treat it as a known false lead.
- No replicated row comes from run 4, because run 4's attribute vocabulary is disjoint from the universal attributes.
