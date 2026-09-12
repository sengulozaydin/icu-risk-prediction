# Pre-model quality review — 2026-09-12

Final artifact: `data/processed/final_dataset.parquet`, 45,253 rows × 85 columns (83 predictors, ICU identifier, target). No duplicate ICU IDs, missing targets, infinities or unexpected death/discharge predictor columns. Target: 39,893 survivors, 5,360 hospital deaths.

## Corrections at source

- Notebook 02: native-unit vital range filtering before temperature conversion and aggregation; ERROR-marked values become NaN. 6,840 feature cells changed. GCS values were already valid. Original raw vital-event cache unchanged.
- Notebook 01: two nonpositive hemoglobin and two nonpositive INR records invalidated before first/last/change calculation. Six feature cells changed. Uncleaned regeneration from raw labs matched the original table first. Negative changes and the negative anion gap were retained.
- Notebook 03: existing negative urine exclusion moved upstream so the first saved table is already correct. The 555,975 mL raw entry was removed by the explicit gross-error screen (>100,000 mL per urine entry); ICU 247320 now totals 5,215 mL. ICU 223940 remains 1,200 mL. EBL and chest-tube flags are byte-value-equivalent to their previous table columns.
- Notebook 06: validated joins, patient/admission target mapping, EBL=0 only for ebl_present=0, predictor/target separation, exact schema and missingness checks; source Parquets are joined rather than temporarily patched.
- Shared rules: `scripts/data_quality.py`. No feature selection changes or new model features.

## Missingness preserved

424,942 missing cells: lab 245,988; vital 176,204; urine 2,750. There are 40,043 rows with at least one missing feature; all remain. Per-column counts are in `data_quality_missing.csv`. Lab/vital missing-table indicators retain their original row-presence semantics. No individual NaN imputation or category encoding.

## Open clinical review items

Structural sanity checks passed; this is not a claim that every retained extreme is valid. See `data_quality_review_flags.csv` for feature-specific counts. Tiny positive vital readings, temperatures outside 26–45 C, unusually high lab endpoints and 9 urine totals above 20 L/day remain flagged. The maximum retained urine total is 98,280 mL and comprises multiple high source records; verify measurement/irrigation context before deciding on exclusion. Do not infer a corrected value. EBL max 50,000 mL and present-row p99/p99.5/p99.9 of 10,000/13,685/25,000 mL remain unchanged.

Fit imputation, scaling and any learned outlier rules only on training data. Use patient-level groups for splits and keep HOSPITAL_EXPIRE_FLAG out of predictors. This audit verifies column-level leakage and existing chart-time windows, not a complete historical-availability reconstruction.

Cohort, intervention, demographics, raw vital cache and unrelated notebooks were checked unchanged by SHA-256. No commit or push.
