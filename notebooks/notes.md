
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


## Filtering ICU Stays by Minimum 24-Hour Length of Stay

Since the goal of the project is to predict mortality using the first 24 hours of ICU data, patients with ICU stays shorter than 24 hours were examined separately.

Among adult ICU records:

- 8,076 ICU stays were shorter than 24 hours.
- 6,902 of these patients survived.
- 1,174 died in the hospital.

For ICU stays of at least 24 hours:

- 45,253 records remained.
- 39,893 patients survived.
- 5,360 died in the hospital.

To ensure that every patient has a complete 24-hour observation window, ICU stays shorter than 24 hours were excluded from the main analysis.

The filtered adult ICU dataset contains:

- 45,253 rows
- 16 columns

This filtered dataset will be used for the next stages of laboratory and clinical feature selection.



## Laboratory Feature Selection and First 24-Hour Extraction

### 1. Defining the Main Prediction Scope

The current project scope was narrowed to **hospital mortality prediction**.

Although the dataset can also support future projects such as:

- Sepsis prediction
- Acute kidney injury / renal failure prediction
- Cardiac event prediction

these outcomes will be handled as separate future projects to keep the current analysis focused and manageable.

---

### 2. Restricting LABEVENTS to the Target ICU Cohort

The laboratory dataset was restricted to hospital admissions belonging to the previously defined adult ICU cohort with stays of at least 24 hours.

After filtering, the laboratory dataset contained:

- **20,166,734 laboratory records**

This ensured that laboratory feature selection was based only on the population that will actually be used in the mortality model.

---

### 3. Measuring Laboratory Test Frequency

For each laboratory test, the number of unique hospital admissions in which the test was performed was calculated.

The tests were then ranked from the most common to the least common.

A frequency threshold of **50% of the target ICU admissions** was used as an initial screening criterion.

Since the target cohort contains 45,253 ICU stays, the approximate 50% threshold was:

- **22,627 admissions**

Using this threshold reduced the laboratory test pool from approximately **726 ITEMIDs to 60 commonly performed tests**.

---

### 4. Reviewing the 60 Most Common Laboratory Tests

The 60 common laboratory ITEMIDs were matched with the laboratory dictionary to obtain:

- Test name
- Specimen type
- Laboratory category

This allowed clinically irrelevant, duplicated or overly specific variables to be removed.

Several urine-based tests and redundant hematological indices were excluded.

Examples of excluded variables included:

- Urine Color
- Urine Appearance
- Yeast
- Epithelial Cells
- MCV
- MCH
- MCHC
- RDW

When multiple variables provided very similar information, the more clinically useful or general variable was preferred.

Examples:

- Hemoglobin was preferred over Hematocrit and RBC count.
- INR was retained while PT and PTT were removed.
- Chemistry Glucose was retained instead of urine or blood-gas glucose.
- Standard Potassium was retained instead of whole-blood potassium.
- Blood pH was retained instead of urine pH.
- Total Calcium was retained instead of Free Calcium.
- Bicarbonate and Anion Gap were retained while Base Excess was excluded.

AST and ALT were both retained because they may provide complementary information about liver injury and overall disease severity.

---

### 5. Final Laboratory Candidate Set

A final set of **23 laboratory features** was selected for mortality prediction:

- Creatinine
- Urea Nitrogen
- Hemoglobin
- Platelet Count
- White Blood Cells
- Sodium
- Potassium
- Chloride
- Bicarbonate
- Anion Gap
- Glucose
- Magnesium
- Calcium, Total
- Phosphate
- INR(PT)
- Blood pH
- pO2
- pCO2
- Lactate
- Albumin
- Bilirubin, Total
- AST
- ALT

These variables were selected based on a combination of:

- Frequency
- Clinical relevance
- Redundancy reduction
- Suitability for early mortality prediction

---

### 6. Extracting Real Measurements for the Selected Tests

The selected 23 laboratory test codes were used to filter the laboratory event table.

This produced:

- **9,978,641 laboratory records**

At this stage, the dataset contained only real measurements belonging to the selected laboratory tests.

---

### 7. Handling Multiple ICU Stays Within the Same Hospital Admission

A single hospital admission can contain more than one ICU stay.

This was checked explicitly.

Result:

- **2,399 hospital admissions had more than one ICU stay**

Because LABEVENTS contains hospital admission IDs but not ICU stay IDs, laboratory records cannot be directly assigned to a specific ICU stay using IDs alone.

Therefore, ICU timing information was used to connect laboratory measurements with the correct ICU stay.

---

### 8. Preparing ICU Timing Information

A lightweight ICU mapping table was created containing only:

- Hospital admission ID
- ICU stay ID
- ICU admission time

The resulting mapping table contained:

- **45,253 rows**
- **3 columns**

This smaller helper table was created to reduce memory usage during the laboratory-ICU matching process.

---

### 9. Improving Datetime Handling

The laboratory timestamp column initially required conversion from text to datetime.

Because the selected laboratory dataset contained nearly 10 million rows, converting the entire column after loading caused excessive memory pressure.

To avoid this issue, the laboratory file was reloaded with the timestamp parsed directly as datetime during file reading.

This reduced the need for a large post-loading datetime conversion step.

---

### 10. Memory-Efficient ICU Matching and First 24-Hour Filtering

A direct merge between the nearly 10-million-row laboratory table and the ICU mapping table caused memory instability.

To avoid this, the laboratory data was processed in **chunks of 500,000 rows**.

For each chunk:

1. Laboratory records were matched with ICU information using the hospital admission ID.
2. The laboratory measurement time was compared with the ICU admission time.
3. Only measurements occurring between ICU admission and the following 24 hours were retained.
4. The filtered chunks were concatenated back into a single dataframe.

Chunking was used only as a memory-management technique. No part of the dataset was intentionally excluded.

The resulting first-24-hour laboratory dataset contained:

- **1,735,994 rows**
- **7 columns**

---

### 11. Current Laboratory Dataset Structure

The current laboratory dataset is still in **long format**.

This means that:

- One row represents one laboratory measurement.
- The same ICU stay can appear in multiple rows.
- Different laboratory tests for the same patient are currently stored vertically.

Example structure:

- ICU stay
- Laboratory test code
- Measurement time
- Laboratory value

The next step will be to decide how repeated measurements of the same test within the first 24 hours should be summarized before converting the dataset into a patient-level wide feature table.


## Laboratory Feature Engineering Notes

- The first 24-hour laboratory data was converted from long format to one row per ICU stay.
- For each selected laboratory test, the first and last measurements were identified.
- Instead of keeping the last value directly, a change feature was created:

  **change = last value - first value**

- Final lab structure uses:
  - `Test_first`
  - `Test_change`

- Highly missing liver-related features were removed:
  - AST
  - ALT
  - Bilirubin
  - Albumin

- Lactate, pH, pO2 and pCO2 were retained despite higher missingness because of their clinical relevance.

- Final laboratory table shape:
  - **44,626 ICU stays**
  - **39 columns**

- The original target cohort had 45,253 ICU stays, so **627 ICU stays had no usable selected laboratory measurements in the first 24 hours**.

These 627 ICU stays were not removed yet. They may still contain useful information from other clinical data sources.


## Processed Data and New Notebook

The processed first-24-hour laboratory feature table was saved as a Parquet file to avoid rerunning the full raw-data pipeline.

A new notebook, `02_feature_engineering.ipynb`, was created to continue feature engineering using the saved processed data.


## Vital Signs Feature Engineering

Vital sign records from the first 24 hours of each ICU stay were processed.

- Fahrenheit temperatures were converted to Celsius and merged under a single `Temperature` variable.
- For each ICU stay and each vital sign, `first`, `last`, `min`, and `max` values were calculated.
- The data was pivoted so that each ICU stay represents one row.
- Missing value rates were checked for all vital features.
- GCS had the highest missingness (~44%) but was kept because of its clinical importance.
