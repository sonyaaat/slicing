# Sliceability v5 — corpus run 1, step 7 (confirmation)

Run `20261017T030528Z`. Rules registered at 2026-10-17T12:28:30+00:00 (UTC); confirmation split read for the first time at 2026-10-17T14:02:39+00:00 after verifying that the tables are byte-identical to the registered ones. No model call.

Criterion: same sign as on discovery, support ≥ 40 on confirmation, and the 95% bootstrap interval (2000 resamples) of the rule mean excludes the confirmation-split mean. Discovery n = 2416, confirmation n = 1611. Deviations are in the table's relative target (score minus theme mean); `shrinkage` = confirmation deviation / discovery deviation. Permutation p is for information only.

## 1. Preregistered rules — 2 of 10 confirmed

Judged on the run target `score_rel_mean`; the per-model columns apply the same criterion to score_rel_gpt and score_rel_claude.

| id | rule | tables | support_disc | dev_disc | support_conf | dev_conf | ci_low | ci_high | conf_split_mean | shrinkage | sign_same | support_ok | ci_excludes_mean | confirmed | gpt_confirmed | claude_confirmed | perm_p_conf |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | possible trigger = stress/exertion AND output constraints = no explicit output constraint | gpt,claude,mean | 85 | -0.0824 | 62 | 0.0111 | -0.0424 | 0.0583 | -0.0027 | -0.1352 | False | True | False | False | False | False | 0.7119 |
| 2 | evidence basis = guideline/standard AND theme = communication | gpt,claude,mean | 163 | -0.0826 | 101 | -0.0640 | -0.1173 | -0.0162 | -0.0027 | 0.7746 | True | True | True | True | True | True | 0.0073 |
| 3 | care setting = hospital/emergency care AND intervention type = procedure/device | gpt,claude,mean | 101 | -0.0696 | 59 | -0.0683 | -0.1282 | -0.0130 | -0.0027 | 0.9808 | True | True | True | True | False | True | 0.0283 |
| 4 | episode timing = not_stated AND care setting = home/community | gpt,mean | 86 | -0.0578 | 55 | 0.0233 | -0.0444 | 0.0842 | -0.0027 | -0.4036 | False | True | False | False | False | False | 0.4604 |
| 5 | intervention type = no intervention AND theme = health_data_tasks | claude,mean | 70 | -0.0630 | 46 | -0.0532 | -0.1250 | 0.0179 | -0.0027 | 0.8437 | True | True | False | False | False | False | 0.1365 |
| 6 | symptom course = stable/improving AND source material = facts to make a document | claude,mean | 79 | 0.0652 | 58 | -0.0372 | -0.1019 | 0.0213 | -0.0027 | -0.5713 | False | True | False | False | False | False | 0.2462 |
| 7 | possible trigger = environment food and travel AND symptom course = not_stated | claude,mean | 96 | -0.0514 | 48 | -0.0185 | -0.0883 | 0.0469 | -0.0027 | 0.3592 | True | True | False | False | False | False | 0.5983 |
| 8 | symptom course = stable/improving AND intervention type = no intervention | gpt | 72 | -0.0656 | 64 | -0.0072 | -0.0684 | 0.0482 | -0.0027 | 0.1103 | True | True | False | False | False | False | 0.8128 |
| 9 | episode timing = happening now/today AND possible trigger = injury/physical contact | gpt | 106 | 0.0567 | 74 | 0.0277 | -0.0242 | 0.0779 | -0.0027 | 0.4892 | True | True | False | False | False | False | 0.3246 |
| 10 | episode timing = weeks months and recurring AND theme = health_data_tasks | gpt | 81 | 0.0575 | 54 | 0.0047 | -0.0598 | 0.0641 | -0.0027 | 0.0818 | True | True | False | False | False | False | 0.8848 |


## 2. k of m per table

| table | confirmed (k) | rows (m) |
|---|---|---|
| et_gpt | 1 | 8 |
| et_claude | 2 | 8 |
| et_mean | 2 | 8 |
| et_diff | 0 | 0 |
| et_gpt_conj3 | 2 | 8 |
| et_claude_conj3 | 2 | 8 |
| et_mean_conj3 | 2 | 8 |
| et_diff_conj3 | 0 | 0 |


**et_gpt**

| step | rule | support_disc | dev_disc | support_conf | dev_conf | ci_low | ci_high | shrinkage | confirmed | perm_p_conf |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | evidence basis = guideline/standard AND theme = communication | 163 | -0.0903 | 101 | -0.0641 | -0.1175 | -0.0153 | 0.7103 | True | 0.0129 |
| 2 | possible trigger = stress/exertion AND output constraints = no explicit output constraint | 85 | -0.0830 | 62 | 0.0348 | -0.0285 | 0.0896 | -0.4186 | False | 0.2916 |
| 3 | care setting = hospital/emergency care AND intervention type = procedure/device | 101 | -0.0664 | 59 | -0.0520 | -0.1206 | 0.0112 | 0.7831 | False | 0.1222 |
| 4 | episode timing = not_stated AND care setting = home/community | 86 | -0.0638 | 55 | 0.0289 | -0.0441 | 0.0966 | -0.4532 | False | 0.4036 |
| 5 | symptom course = stable/improving AND intervention type = no intervention | 72 | -0.0639 | 64 | -0.0075 | -0.0767 | 0.0549 | 0.1171 | False | 0.8135 |
| 6 | episode timing = happening now/today AND possible trigger = environment food and travel | 62 | -0.0588 | 42 | 0.0374 | -0.0286 | 0.0969 | -0.6349 | False | 0.3485 |
| 7 | episode timing = happening now/today AND possible trigger = injury/physical contact | 106 | 0.0599 | 74 | 0.0312 | -0.0261 | 0.0821 | 0.5205 | False | 0.2983 |
| 8 | episode timing = weeks months and recurring AND theme = health_data_tasks | 81 | 0.0665 | 54 | -0.0262 | -0.0960 | 0.0401 | -0.3936 | False | 0.4546 |


**et_claude**

| step | rule | support_disc | dev_disc | support_conf | dev_conf | ci_low | ci_high | shrinkage | confirmed | perm_p_conf |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | evidence basis = guideline/standard AND theme = communication | 163 | -0.0750 | 101 | -0.0639 | -0.1220 | -0.0127 | 0.8519 | True | 0.0122 |
| 2 | evidence basis = no outside basis AND theme = communication | 289 | 0.0532 | 199 | 0.0127 | -0.0309 | 0.0550 | 0.2386 | False | 0.4750 |
| 3 | possible trigger = stress/exertion AND output constraints = no explicit output constraint | 85 | -0.0818 | 62 | -0.0125 | -0.0730 | 0.0429 | 0.1526 | False | 0.7095 |
| 4 | symptom course = stable/improving AND source material = facts to make a document | 79 | 0.0830 | 58 | -0.0271 | -0.0968 | 0.0355 | -0.3271 | False | 0.4363 |
| 5 | intervention type = no intervention AND theme = health_data_tasks | 70 | -0.0764 | 46 | -0.0358 | -0.1281 | 0.0532 | 0.4685 | False | 0.3637 |
| 6 | care setting = hospital/emergency care AND intervention type = procedure/device | 101 | -0.0729 | 59 | -0.0846 | -0.1494 | -0.0245 | 1.1608 | True | 0.0134 |
| 7 | possible trigger = environment food and travel AND symptom course = not_stated | 96 | -0.0637 | 48 | -0.0262 | -0.1068 | 0.0476 | 0.4106 | False | 0.4909 |
| 8 | source material = no source material AND output constraints = exact length/size | 83 | -0.0720 | 49 | -0.0276 | -0.1088 | 0.0534 | 0.3830 | False | 0.4714 |


**et_mean**

| step | rule | support_disc | dev_disc | support_conf | dev_conf | ci_low | ci_high | shrinkage | confirmed | perm_p_conf |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | evidence basis = guideline/standard AND theme = communication | 163 | -0.0826 | 101 | -0.0640 | -0.1170 | -0.0156 | 0.7746 | True | 0.0054 |
| 2 | possible trigger = stress/exertion AND output constraints = no explicit output constraint | 85 | -0.0824 | 62 | 0.0111 | -0.0425 | 0.0586 | -0.1352 | False | 0.7189 |
| 3 | care setting = hospital/emergency care AND intervention type = procedure/device | 101 | -0.0696 | 59 | -0.0683 | -0.1296 | -0.0117 | 0.9808 | True | 0.0251 |
| 4 | possible trigger = environment food and travel AND symptom course = not_stated | 96 | -0.0514 | 48 | -0.0185 | -0.0905 | 0.0487 | 0.3592 | False | 0.5986 |
| 5 | intervention type = no intervention AND theme = health_data_tasks | 70 | -0.0630 | 46 | -0.0532 | -0.1242 | 0.0167 | 0.8437 | False | 0.1298 |
| 6 | symptom course = stable/improving AND source material = facts to make a document | 79 | 0.0652 | 58 | -0.0372 | -0.1001 | 0.0211 | -0.5713 | False | 0.2381 |
| 7 | source material = no source material AND theme = complex_responses | 98 | -0.0525 | 55 | -0.0364 | -0.0999 | 0.0204 | 0.6933 | False | 0.2691 |
| 8 | episode timing = not_stated AND care setting = home/community | 86 | -0.0578 | 55 | 0.0233 | -0.0413 | 0.0856 | -0.4036 | False | 0.4736 |


**et_gpt_conj3**

| step | rule | support_disc | dev_disc | support_conf | dev_conf | ci_low | ci_high | shrinkage | confirmed | perm_p_conf |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | evidence basis = guideline/standard AND theme = communication | 163 | -0.0903 | 101 | -0.0641 | -0.1182 | -0.0165 | 0.7103 | True | 0.0106 |
| 2 | evidence basis = no outside basis AND possible trigger = stress/exertion AND output constraints = no explicit output constraint | 79 | -0.0913 | 56 | 0.0411 | -0.0262 | 0.1032 | -0.4506 | False | 0.2338 |
| 3 | care setting = not_stated AND source material = no source material AND theme = communication | 120 | 0.0505 | 72 | 0.1017 | 0.0315 | 0.1609 | 2.0153 | True | 0.0007 |
| 4 | patient age = not_stated AND request structure = one focused task AND theme = emergency_referrals | 164 | 0.0566 | 112 | 0.0198 | -0.0339 | 0.0726 | 0.3504 | False | 0.4106 |
| 5 | episode timing = weeks months and recurring AND request structure = one focused task AND theme = health_data_tasks | 67 | 0.0792 | 45 | -0.0255 | -0.0977 | 0.0434 | -0.3221 | False | 0.5055 |
| 6 | care setting = hospital/emergency care AND intervention type = procedure/device AND request structure = one focused task | 83 | -0.0777 | 50 | -0.0476 | -0.1218 | 0.0277 | 0.6129 | False | 0.1983 |
| 7 | patient age = not_stated AND possible trigger = medicine/medical treatment AND symptom course = not_stated | 105 | 0.0675 | 65 | 0.0441 | -0.0221 | 0.1026 | 0.6532 | False | 0.1686 |
| 8 | episode timing = not_stated AND care setting = home/community AND request structure = one focused task | 60 | -0.0820 | 42 | 0.0204 | -0.0675 | 0.0989 | -0.2493 | False | 0.6114 |


**et_claude_conj3**

| step | rule | support_disc | dev_disc | support_conf | dev_conf | ci_low | ci_high | shrinkage | confirmed | perm_p_conf |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | evidence basis = no outside basis AND possible trigger = not_stated AND theme = communication | 159 | 0.0837 | 97 | 0.0106 | -0.0476 | 0.0656 | 0.1266 | False | 0.6819 |
| 2 | evidence basis = no outside basis AND care setting = home/community AND theme = communication | 93 | -0.0621 | 73 | -0.0804 | -0.1424 | -0.0194 | 1.2962 | True | 0.0095 |
| 3 | evidence basis = guideline/standard AND theme = communication | 163 | -0.0750 | 101 | -0.0639 | -0.1188 | -0.0129 | 0.8519 | True | 0.0133 |
| 4 | possible trigger = not_stated AND symptom course = not_stated AND intervention type = procedure/device | 153 | -0.0555 | 99 | -0.0456 | -0.1002 | -0.0003 | 0.8220 | False | 0.0795 |
| 5 | possible trigger = injury/physical contact AND care setting = home/community AND request structure = one focused task | 80 | 0.0734 | 59 | -0.0008 | -0.0682 | 0.0580 | -0.0105 | False | 0.9816 |
| 6 | episode timing = weeks months and recurring AND symptom course = getting worse AND output constraints = no explicit output constraint | 62 | 0.1034 | 42 | 0.0707 | -0.0085 | 0.1491 | 0.6834 | False | 0.0845 |
| 7 | symptom course = stable/improving AND source material = facts to make a document | 79 | 0.0830 | 58 | -0.0271 | -0.0951 | 0.0380 | -0.3271 | False | 0.4336 |
| 8 | evidence basis = no outside basis AND symptom course = stable/improving AND intervention type = no intervention | 64 | -0.0781 | 57 | -0.0045 | -0.0792 | 0.0656 | 0.0579 | False | 0.8977 |


**et_mean_conj3**

| step | rule | support_disc | dev_disc | support_conf | dev_conf | ci_low | ci_high | shrinkage | confirmed | perm_p_conf |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | evidence basis = guideline/standard AND theme = communication | 163 | -0.0826 | 101 | -0.0640 | -0.1179 | -0.0190 | 0.7746 | True | 0.0073 |
| 2 | possible trigger = not_stated AND source material = no source material AND theme = communication | 188 | 0.0566 | 100 | 0.0276 | -0.0291 | 0.0791 | 0.4867 | False | 0.2475 |
| 3 | evidence basis = no outside basis AND care setting = home/community AND theme = communication | 93 | -0.0572 | 73 | -0.0611 | -0.1196 | -0.0111 | 1.0682 | True | 0.0293 |
| 4 | evidence basis = no outside basis AND possible trigger = stress/exertion AND output constraints = no explicit output constraint | 79 | -0.0873 | 56 | 0.0091 | -0.0494 | 0.0633 | -0.1039 | False | 0.7799 |
| 5 | episode timing = weeks months and recurring AND symptom course = getting worse AND output constraints = no explicit output constraint | 62 | 0.0918 | 42 | 0.0536 | -0.0224 | 0.1273 | 0.5835 | False | 0.1545 |
| 6 | episode timing = not_stated AND possible trigger = not_stated AND intervention type = procedure/device | 64 | -0.0732 | 41 | -0.0722 | -0.1565 | 0.0042 | 0.9856 | False | 0.0580 |
| 7 | symptom course = stable/improving AND source material = facts to make a document | 79 | 0.0652 | 58 | -0.0372 | -0.1018 | 0.0215 | -0.5713 | False | 0.2451 |
| 8 | evidence basis = no outside basis AND symptom course = stable/improving AND intervention type = no intervention | 64 | -0.0725 | 57 | -0.0052 | -0.0726 | 0.0569 | 0.0719 | False | 0.8758 |


## 3. Confirmed rules on all 4,027 messages (worst slice first)

Points = deviation × 100. Percent = deviation / corpus mean of the clipped score (gpt 0.5007, claude 0.4914, mean 0.4960). `rel` = relative target (theme-centred), `clip` = clipped score, `raw` = unclipped score. Worst axis: per model, achieved points on the axis / total positive points (sums to the unclipped score), centred on the theme mean; row term = mean(row) - mean(all), averaged over gpt and claude; the axis with the largest term in the direction of the deviation; n = rule messages with a criterion on that axis.

| rule | preregistered_id | confirmed_in | n_full | themes | mean_rel_dev_pts | mean_rel_dev_pct | gpt_rel_dev_pts | claude_rel_dev_pts | mean_clipped_dev_pts | mean_raw_dev_pts | mean_raw_dev_pct | worst_axis | worst_axis_term_pts | worst_axis_n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| evidence basis = guideline/standard AND theme = communication | 2.00 | gpt#1, claude#1, mean#1, gpt_conj3#1, claude_conj3#3, mean_conj3#1, prereg#2 | 264 | 1 | -7.54 | -15.21 | -8.02 | -7.07 | 2.82 | 2.42 | 4.98 | communication_quality | -6.43 | 198 |
| care setting = hospital/emergency care AND intervention type = procedure/device | 3.00 | claude#6, mean#3, prereg#3 | 160 | 7 | -6.90 | -13.91 | -6.09 | -7.71 | -5.50 | -6.47 | -13.30 | context_awareness | -6.69 | 104 |
| evidence basis = no outside basis AND care setting = home/community AND theme = communication |  | claude_conj3#2, mean_conj3#3 | 166 | 1 | -5.91 | -11.92 | -4.79 | -7.03 | 4.45 | 4.86 | 9.99 | accuracy | -6.65 | 161 |


**— corpus mean —**

| rule | preregistered_id | confirmed_in | n_full | themes | mean_rel_dev_pts | mean_rel_dev_pct | gpt_rel_dev_pts | claude_rel_dev_pts | mean_clipped_dev_pts | mean_raw_dev_pts | mean_raw_dev_pct | worst_axis | worst_axis_term_pts | worst_axis_n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| care setting = not_stated AND source material = no source material AND theme = communication |  | gpt_conj3#3 | 192 | 1 | 7.35 | 14.82 | 6.98 | 7.72 | 17.71 | 18.35 | 37.71 | communication_quality | 6.14 | 177 |


## 4. Judgement

**Headline.** 2 of 10 preregistered rules are confirmed (#2, #3). Under the null, a rule
passes "same sign + CI excludes the mean" with probability about 0.025, so 0.25 confirmations
would be expected and P(>= 2 of 10) = 0.025. The result is small but not chance. It sits inside
the 1-3 forecast in the step-6 report and improves on run 4 (0 of 8). Across all tables, 4
distinct rules are confirmed (gpt 1/8, claude 2/8, mean 2/8, each conj3 table 2/8; diff tables
had no rows).

**What survived.**
1. **The only universal finding:** `care setting = hospital/emergency care AND intervention type
   = procedure/device` (prereg #3). Spread over all 7 themes.
   - **Size:** -6.9 points against the theme mean on all 4,027 messages (n = 160); -13.9% of the
     corpus mean score; -6.5 points on the raw unclipped score.
   - **Shrinkage:** 0.98, i.e. the effect held its size.
   - **Models:** confirmed on claude and on the mean; directional on gpt (-0.052, CI reaches
     +0.011).
   - **Worst axis:** context_awareness (-6.7 points; 104 of the 160 messages have a criterion on
     it).
   - **Reading:** messages about a procedure or device in a hospital / emergency setting are
     answered worse than other messages of the same theme, by both models. This is the one rule
     that fits the v5 goal of a situation attribute that applies across the corpus.
2. **Three theme-specific rules, all inside communication:**
   - `evidence basis = guideline/standard AND theme = communication` (prereg #2): -7.5 points
     relative, n = 264, shrinkage 0.77, confirmed on both models separately. Worst axis
     communication_quality (n = 198).
   - `evidence basis = no outside basis AND care setting = home/community AND theme =
     communication`: -5.9.
   - `care setting = not_stated AND source material = no source material AND theme =
     communication`: +7.4, the only confirmed positive slice.

   This matches step 0, where communication was one of the two themes with explained variance
   (R2 0.15). These rules belong to the communication drill-down, not to the universal layer.

   **Raw vs relative sign:** rule #2 is *above* the corpus mean on the raw score (+2.8 points)
   because communication is the highest-scoring theme. "Worse" here means worse than the rest of
   communication. Any table shown to a reader must say which reference it uses.

**What failed, and why that matters.**
- **My first-choice rule failed outright.** #1 (stress/exertion) flipped sign: -0.082 on
  discovery, +0.011 on confirmation. This is the pattern synthetic A warned about: a real-looking
  one-condition group paired with a near-vacuous second condition, picked by information gain
  at effect sizes below the slicer's resolution (~0.1).
- **The outcome is bimodal.** Confirmed rules kept 77-98% of their discovery effect; most
  others collapsed to about 0 or reversed. Three preregistered rules changed sign on the mean
  target (#1, #4, #6; #6 on both models separately), and #10 changed sign on gpt. So the step-6 effects are a mix of a few
  real slices and selection noise, not uniformly inflated real effects.
- **No confirmed rule uses a form attribute.** Every row containing `request structure` or
  `output constraints` failed. They were the most reliable attributes and added nothing that
  held up, which supports the v5 decision to exclude form attributes.
- **Near misses** (same sign, CI includes the mean):
  - #5 `intervention type = no intervention AND theme = health_data_tasks`: -0.053, n = 46;
  - conj3 `episode timing = not_stated AND possible trigger = not_stated AND intervention type =
    procedure/device`: -0.072, n = 41.

  They are not confirmed and must not be reported as such.

**Is the target or the pipeline wrong?** The target behaves as step 0 predicted. The text
explains about 3% of the theme-relative score; what confirms sits in the two themes with signal
or is a 5-7 point effect. Nothing here suggests a bug. Specifically:
- every discovery number reproduced exactly from the stored annotations;
- the tables were byte-identical to the registered ones;
- the confirmation split was read once, after registration.

The pipeline problems are the ones named in the step-6 report:
- form attributes entering through the critic's missing path;
- two core situation attributes lost to the distinctness rule;
- reliability dropping `main request` at 0.797.

Fixing them requires a new run number with a new split or new data. This confirmation split is
now spent.

**What I would write in the paper.**
- One universal confirmed slice (#3, both models, -14% of the mean, context_awareness).
- One confirmed theme-level pattern (guideline-based requests in communication, both models).
- 2 of 10 preregistered rules confirmed, against 0.25 expected by chance.
- A synthetic check showing the slicer resolves planted effects reliably only from about 0.1
  upward, which explains why most 5-point rows did not survive.
- No model-difference slice: diff R2 is about 0 and both diff tables were empty.
