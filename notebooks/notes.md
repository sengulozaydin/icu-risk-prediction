
# 01 — Data Overview

## Objective
Explore the core tables for an ICU risk prediction project.

## Environment
Created a project-specific Python environment and verified pandas.

## Tables Reviewed
- PATIENTS: 46,520 rows and 8 columns.
- ADMISSIONS: 58,976 rows and 19 columns.
- ICUSTAYS: 61,532 rows and 12 columns.

## Initial Findings
- SUBJECT_ID identifies a patient.
- HADM_ID identifies a hospital admission.
- ICUSTAY_ID identifies an ICU stay.
- A patient can have multiple admissions.
- Date columns were loaded as strings.
- OUTTIME and LOS each have 10 missing values in ICUSTAYS.
- LOS represents ICU length of stay in days.

## Core Table Merge
Created icu_base_df with one row per ICU stay.

- Checked the primary identifiers for missing values and duplicates.
- Combined selected columns using validated left joins.
- Preserved all 61,532 ICU stays.
- The merged table contains 13 columns.
- Every ICU stay matched a patient and hospital admission.
- The original DataFrames were kept unchanged.


## Core Table Merge

Selected columns from PATIENTS, ADMISSIONS, and ICUSTAYS were
combined into `icu_base_df`, with one row per ICU stay.

- Checked identifiers for missing values and duplicates.
- Used left joins with many-to-one validation.
- Preserved all 61,532 ICU stays, producing 13 columns.
- Confirmed that every ICU stay matched a patient and hospital admission.
- Kept the original DataFrames unchanged.

## Age Preparation

- Converted birth, hospital admission/discharge, and ICU entry/exit
  columns to datetime.
- Calculated approximate age at ICU entry using INTIME (ICU entry)
  and DOB (date of birth).
- Preserved the original calculation in AGE_RAW.
- MIMIC-III masks ages over 89 by shifting birth dates, which can
  produce calculated ages above 300.
- Created AGE by capping calculated ages at 90.
  The value 90 represents the 90+ group, not an exact age.
- Created AGE_90_PLUS: 1 for calculated ages of 90 or above,
  and 0 otherwise.
- Identified 2,721 ICU stays in the 90+ group.
- No records were removed; all 61,532 ICU stays were retained.
- AGE_RAW will not be used as a model input.


### Age Preparation and Cohort Separation

- Calculated age at ICU admission using the date of birth and ICU admission time.
- Preserved the calculated age in `AGE_RAW`, capped `AGE` at 90, and added `AGE_90_PLUS`. A value of 90 represents the 90+ age group, not an exact age.
- Created separate pediatric (`AGE < 18`) and adult (`AGE >= 18`) DataFrames.
- Before removing missing values:
  - **Pediatric cohort:** 8,200 ICU stays from 7,967 unique patients.
  - **Adult cohort:** 53,332 ICU stays from 38,512 unique patients.
- Removed rows with missing ICU discharge time (`OUTTIME`) or length of stay (`LOS`) from both cohort DataFrames.
- Kept the original merged table, `icu_base_df`, unchanged.


### Early Mortality After ICU Admission

To examine early mortality, we added the death timestamp (`DEATHTIME`) from the admissions table to the adult ICU dataset, matching records by `SUBJECT_ID` and `HADM_ID`.

We calculated the time between ICU admission (`INTIME`) and death in hours, then counted unique patients with a recorded in-hospital death within 24 and 48 hours of ICU admission.

The analysis used the adult cohort before applying minimum 24-hour or 48-hour ICU stay filters, so early deaths were retained. Each patient was counted only once within each time window.

| Time Window | Patients Who Died | Percentage of Adult Patients |
|---|---:|---:|
| Within 24 hours | 1,077 | 2.80% |
| Within 48 hours | 1,806 | 4.69% |

Both percentages used the same denominator: **38,510 unique adult ICU patients**. Bar charts displayed the patient counts and percentages.

These windows are cumulative: deaths within 24 hours are also included in the 48-hour total. For patients with multiple ICU stays, a qualifying death could be identified relative to any recorded ICU admission, not only their first.

These results describe recorded in-hospital deaths following ICU admission; they do not require death to have occurred inside the ICU. This is a descriptive analysis, separate from the prediction task.
