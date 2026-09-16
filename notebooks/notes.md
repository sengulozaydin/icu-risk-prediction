
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


## Urine Output Feature Engineering

- Urine-related records were identified from `OUTPUTEVENTS` using relevant `ITEMID` values.
- Only raw urine volume records were kept; rate-based and irrigation-related records were excluded.
- Urine records were matched with ICU admission time (`INTIME`).
- Only measurements within the first 24 hours of each ICU stay were retained.
- Total urine output was calculated for each `ICUSTAY_ID`.
- `ICUSTAY_ID` was converted to integer format.
- Missingness was checked against the full cohort of 45,253 ICU stays.
- Urine output was missing in 2,665 stays (~5.89%).


## Additional Output Features

- Chest tube-related output records were identified from `OUTPUTEVENTS`.
- Chest tube output was converted into a binary feature: `chest_tube_present`.
- `chest_tube_present = 1` indicates a chest tube record within the first 24 hours, otherwise `0`.
- EBL (Estimated Blood Loss) records were identified from OR and PACU output items.
- Two EBL features were created:
  - `ebl_present`: whether an EBL record exists in the first 24 hours.
  - `ebl_24h`: total estimated blood loss in the first 24 hours.
- EBL showed strong outliers, but they were kept unchanged for later model-stage evaluation.
- Urine, chest tube, and EBL features were combined into a single output feature table.
- The final table was saved as `output_features_first24h.parquet`.


## First 24-Hour Intervention Features

- Three binary intervention features were created: mechanical ventilation, vasopressor use, and RRT/CRRT.
- Only events occurring within the first 24 hours after ICU admission were used.
- Standard MIMIC-III source tables and ITEMID definitions were used.
- The final table contains 45,253 unique ICU stays with no missing values.
- Mechanical ventilation was present in 47.86%, vasopressor use in 30.20%, and RRT/CRRT in 2.57% of ICU stays.


# Demographic and admission features

Use the existing adult ICU cohort without filtering, reordering or expanding it. Output exactly `ICUSTAY_ID`, `age`, `gender`, `admission_type`, `admission_location` to `data/processed/demographic_features.parquet`.

## Sources and timing

- Existing `adult_icu_cohort_first24h.parquet`: ICUSTAY_ID, SUBJECT_ID, HADM_ID, INTIME.
- PATIENTS: **only SUBJECT_ID, DOB, GENDER**; left join on SUBJECT_ID with many-to-one validation.
- ADMISSIONS: **only SUBJECT_ID, HADM_ID, ADMISSION_TYPE, ADMISSION_LOCATION**; left join on both hospital-admission and patient identifiers with many-to-one validation.

No death, discharge, outcome, insurance, marital status, ethnicity, religion or language columns are read. Admission attributes are treated as information available at hospital admission; no later measurement or treatment information is used. The retrospective source does not provide field-level revision history.

## Age policy

Compute continuous age at ICU entry as `(INTIME - DOB).total_seconds() / (365.25 * 86400)`. Use microsecond datetime resolution to avoid overflowing nanosecond timedeltas when DOB is shifted by centuries. Do not round age before applying the adult-cohort checks.

[MIMIC-III PATIENTS documentation](https://mimic.mit.edu/docs/iii/tables/patients.html) explains that DOB is shifted for older patients, yielding ages near 300 years. Following the existing project's top-coding convention, cap calculated ages at **90**. The value 90 represents the upper age group, including anonymized older patients; it is not a recovered exact age. No age-group column is added. Missing source values remain missing; no imputation or category encoding is applied. Original category strings, including explicit unknown categories, are preserved.


## Final Dataset Preparation and Quality Control

- Lab, vital, output, intervention, and demographic feature tables were merged using `ICUSTAY_ID`.
- The full cohort of 45,253 ICU stays was preserved with no duplicate IDs.
- Two missingness indicators were added: `lab_missing` and `vital_missing`.
- `HOSPITAL_EXPIRE_FLAG` was added as the mortality target.
- EBL missing values were set to 0 only when no EBL record was present.
- Source-level data quality checks were performed for labs, vitals, urine output, and extreme values.
- Invalid urine and vital measurements were corrected at the source feature level.
- Leakage, duplicate IDs, infinite values, and impossible negative values were checked.
- Remaining lab, vital, and urine missing values were intentionally preserved for later imputation.
- Final dataset: **45,253 rows × 85 columns**.



## Train-Test Split

The final dataset was prepared for machine learning by separating predictors, target, and patient identifiers.

- `HOSPITAL_EXPIRE_FLAG` was defined as the target variable.
- `SUBJECT_ID` was used only to keep multiple ICU stays from the same patient in the same split.
- `ICUSTAY_ID` and `SUBJECT_ID` were excluded from model predictors.
- The data was split into approximately 80% training and 20% test sets.
- `GroupShuffleSplit` was used to prevent ICU stays from the same patient from appearing in both training and test sets.


## Preprocessing and Cross-Validation Setup

- The training data was separated into numerical and categorical feature groups.
- Numerical features were assigned a median imputation strategy using `SimpleImputer`.
- Categorical features were assigned a `OneHotEncoder` with unknown-category handling.
- Both preprocessing steps were combined using `ColumnTransformer`.
- `StratifiedGroupKFold` was prepared for 5-fold cross-validation.
- Patient-level grouping will use `SUBJECT_ID` so that multiple ICU stays from the same patient remain in the same fold.
- A final sanity check confirmed 3 categorical features, 80 numerical features, and a training shape of `(36169, 83)`.



## Logistic Regression

Logistic Regression was used as the first baseline classification model for ICU mortality prediction.

- Numerical features were processed with median imputation followed by `StandardScaler`.
- Categorical features were transformed using `OneHotEncoder`.
- Preprocessing and Logistic Regression were combined in a single pipeline.
- Model performance was evaluated using 5-fold `StratifiedGroupKFold`, keeping ICU stays from the same patient in the same fold.
- The baseline model achieved approximately:
  - ROC-AUC: **0.84**
  - Precision: **0.64**
  - Recall: **0.24**
  - F1: **0.35**
- Because mortality represented the minority class, `class_weight="balanced"` was also tested.
- The balanced model increased recall to approximately **0.74**, but reduced precision to approximately **0.31**.
- Threshold tuning was then applied to both models.
- For the standard Logistic Regression, a threshold of **0.20** provided a more suitable trade-off for this clinical task:
  - Precision: **0.40**
  - Recall: **0.57**
  - F1: **0.47**
- For the balanced Logistic Regression, a threshold of **0.70** produced:
  - Precision: **0.43**
  - Recall: **0.52**
  - F1: **0.47**
- Since identifying high-risk patients is especially important in this project, the standard Logistic Regression with a **0.20 threshold** was retained as the stronger Logistic Regression candidate due to its higher recall.


## K-Nearest Neighbors (KNN)

KNN was evaluated as a distance-based classification model for ICU mortality prediction.

- Numerical features were processed using median imputation followed by `StandardScaler`.
- Categorical features were transformed using `OneHotEncoder`.
- Preprocessing and KNN were combined in a single pipeline.
- Model performance was evaluated with 5-fold `StratifiedGroupKFold`, keeping ICU stays from the same patient in the same fold.
- Different `n_neighbors` values were tested.
- Without class balancing, KNN showed low recall. The best recall among the tested standard KNN models was obtained with `K=3`:
  - ROC-AUC: **0.67**
  - Precision: **0.52**
  - Recall: **0.17**
  - F1: **0.25**
- Because mortality is the minority class, SMOTE was then applied inside the cross-validation pipeline.
- SMOTE substantially increased recall but reduced precision.
- With SMOTE:
  - `K=3`: Precision **0.24**, Recall **0.71**, F1 **0.35**
  - `K=5`: Precision **0.23**, Recall **0.75**, F1 **0.35**
  - `K=7`: Precision **0.22**, Recall **0.78**, F1 **0.35**
- `K=3 + SMOTE` was retained as the most balanced KNN candidate because it provided the highest precision and F1 among the SMOTE-based KNN models while maintaining high recall.
- Overall, KNN showed a weaker precision-recall balance than Logistic Regression for this dataset.



## Decision Tree

A Decision Tree classifier was evaluated for ICU mortality prediction.

- Numerical features were processed using median imputation.
- Categorical features were transformed using `OneHotEncoder`.
- StandardScaler was not used because Decision Tree models are not sensitive to feature scaling.
- Model performance was evaluated using 5-fold `StratifiedGroupKFold`, keeping ICU stays from the same patient in the same fold.

### Baseline Decision Tree

The default Decision Tree showed weak performance:

- ROC-AUC: **0.621**
- Precision: **0.323**
- Recall: **0.339**
- F1: **0.331**

### Hyperparameter Tuning

`GridSearchCV` was used to test different values of:

- `max_depth`
- `min_samples_split`
- `min_samples_leaf`

The best parameters were:

- `max_depth = 5`
- `min_samples_leaf = 5`
- `min_samples_split = 2`

With these parameters:

- ROC-AUC: **0.760**
- Precision: **0.577**
- Recall: **0.142**
- F1: **0.226**

Although ROC-AUC improved substantially, recall became very low.

### Class Weight Balancing

Because mortality is the minority class, `class_weight="balanced"` was added to the tuned Decision Tree.

Performance improved to:

- ROC-AUC: **0.772**
- Precision: **0.253**
- Recall: **0.701**
- F1: **0.371**

Class weighting substantially increased recall, but precision decreased due to a higher number of false-positive predictions.

### Threshold Tuning

Different probability thresholds were evaluated for the tuned and balanced Decision Tree:

- Threshold `0.5`: Precision **0.252**, Recall **0.701**, F1 **0.370**
- Threshold `0.6`: Precision **0.312**, Recall **0.536**, F1 **0.394**
- Threshold `0.7`: Precision **0.356**, Recall **0.442**, F1 **0.394**
- Threshold `0.8`: Precision **0.433**, Recall **0.294**, F1 **0.350**

Increasing the threshold improved precision but reduced recall. The model was not able to achieve high precision and recall simultaneously.

Overall, the tuned and class-balanced Decision Tree provided much better recall than the baseline model, but its precision-recall balance remained limited.



## Random Forest

A Random Forest classifier was evaluated for ICU mortality prediction.

- Numerical features were processed using median imputation.
- Categorical features were transformed using `OneHotEncoder`.
- StandardScaler was not used because Random Forest is not sensitive to feature scaling.
- Model performance was evaluated using 5-fold `StratifiedGroupKFold`, keeping ICU stays from the same patient in the same fold.

### Baseline Random Forest

The default Random Forest produced:

- ROC-AUC: **0.846**
- Precision: **0.741**
- Recall: **0.159**
- F1: **0.262**

The model had strong precision and good discrimination, but recall was very low.

### Hyperparameter Tuning

`GridSearchCV` was used to test different Random Forest settings.

The best parameters were:

- `n_estimators = 200`
- `max_depth = None`
- `min_samples_leaf = 5`
- `max_features = "sqrt"`

With these parameters:

- ROC-AUC: **0.855**
- Precision: **0.798**
- Recall: **0.135**
- F1: **0.231**

Hyperparameter tuning slightly improved ROC-AUC and precision, but recall decreased further.

### Class Weight Balancing

Because mortality is the minority class, `class_weight="balanced"` was added to the tuned Random Forest.

The resulting performance was:

- ROC-AUC: **0.862**
- Precision: **0.455**
- Recall: **0.552**
- F1: **0.498**

Class weighting substantially improved recall while maintaining a reasonable precision level. It also produced the highest F1 score among the tested Random Forest configurations.

Threshold tuning was not applied because precision and recall were already relatively balanced, and changing the threshold would mainly trade one metric for the other rather than improve both simultaneously.

Overall, the tuned and class-balanced Random Forest provided the strongest and most balanced Random Forest performance for this dataset.



## XGBoost

An XGBoost classifier was evaluated for ICU mortality prediction.

- Numerical features were processed using median imputation.
- Categorical features were transformed using `OneHotEncoder`.
- StandardScaler was not used because XGBoost is not sensitive to feature scaling.
- Model performance was evaluated using 5-fold `StratifiedGroupKFold`, keeping ICU stays from the same patient in the same fold.

### Baseline XGBoost

The default XGBoost model produced:

- ROC-AUC: **0.855**
- Precision: **0.606**
- Recall: **0.314**
- F1: **0.413**

The model showed good discrimination and precision, but recall remained relatively low.

### Hyperparameter Tuning

`GridSearchCV` was used to test different XGBoost settings.

The best parameters were:

- `n_estimators = 200`
- `max_depth = 5`
- `learning_rate = 0.1`

With these parameters:

- ROC-AUC: **0.870**
- Precision: **0.666**
- Recall: **0.300**
- F1: **0.414**

Hyperparameter tuning improved ROC-AUC and precision, but recall remained low.

### Class Imbalance Adjustment

Because mortality is the minority class, `scale_pos_weight` was used to give more importance to positive cases.

The class ratio was calculated as:

- Negative class: **31,842**
- Positive class: **4,327**
- `scale_pos_weight ≈ 7.36`

With class balancing:

- ROC-AUC: **0.864**
- Precision: **0.382**
- Recall: **0.680**
- F1: **0.489**

Class balancing substantially increased recall, while precision decreased as expected.

### Threshold Tuning

Different probability thresholds were evaluated using out-of-fold predictions from the tuned and class-balanced XGBoost model.

- Threshold `0.5`: Precision **0.381**, Recall **0.680**, F1 **0.489**
- Threshold `0.6`: Precision **0.446**, Recall **0.587**, F1 **0.507**
- Threshold `0.7`: Precision **0.519**, Recall **0.464**, F1 **0.490**
- Threshold `0.8`: Precision **0.612**, Recall **0.320**, F1 **0.420**

Threshold `0.6` provided the strongest overall precision-recall balance and the highest F1 score.

Overall, the best XGBoost configuration was:

- Tuned hyperparameters
- `scale_pos_weight ≈ 7.36`
- Classification threshold = **0.6**

This configuration achieved a strong balance between precision and recall while maintaining high ROC-AUC.




## Deep Learning

A feed-forward neural network was evaluated for ICU mortality prediction.

- Numerical features were processed using median imputation followed by `StandardScaler`.
- Categorical features were transformed using `OneHotEncoder`.
- The training data was split into train and validation subsets using `StratifiedGroupKFold`, keeping ICU stays from the same patient in the same group.
- A neural network with two hidden layers was used:
  - 64 neurons
  - 32 neurons
  - 1 output neuron
- ReLU activation was used in the hidden layers.
- Sigmoid activation was used in the output layer for binary classification.
- The model was trained with:
  - Optimizer: `Adam`
  - Loss: `binary_crossentropy`
  - Batch size: `64`
  - Maximum epochs: `50`
- `EarlyStopping` with `patience=5` and `restore_best_weights=True` was used to reduce overfitting.

### Baseline Neural Network

The baseline model stopped after 11 epochs due to EarlyStopping.

Validation performance:

- ROC-AUC: **0.864**
- Precision: **0.624**
- Recall: **0.325**
- F1: **0.427**

The model showed good discrimination and precision, but recall remained relatively low.

### Class Weight Balancing

Because mortality is the minority class, class weights were added during model training.

The balanced model stopped after 8 epochs due to EarlyStopping.

Validation performance:

- ROC-AUC: **0.868**
- Precision: **0.350**
- Recall: **0.753**
- F1: **0.477**

Class weighting substantially improved recall, although precision decreased.

### Threshold Tuning

Different classification thresholds were evaluated on the balanced neural network:

- Threshold `0.5`: Precision **0.350**, Recall **0.753**, F1 **0.477**
- Threshold `0.6`: Precision **0.404**, Recall **0.651**, F1 **0.499**
- Threshold `0.7`: Precision **0.484**, Recall **0.532**, F1 **0.507**
- Threshold `0.8`: Precision **0.575**, Recall **0.384**, F1 **0.460**

Threshold `0.7` produced the highest F1 score, but threshold `0.6` was preferred because recall was considered more important for ICU mortality prediction.

Overall, the selected Deep Learning configuration was:

- Two hidden layers: `64 → 32`
- Class weighting enabled
- Classification threshold = **0.6**

This configuration provided a stronger recall-focused balance for the clinical objective.



### Final Model Candidates

Random Forest, XGBoost and Deep Learning were the strongest models overall.

Among them, Deep Learning was selected as the final candidate because recall was the main priority for ICU mortality prediction.

- Random Forest: Precision **0.455**, Recall **0.552**
- XGBoost: Precision **0.446**, Recall **0.587**
- Deep Learning: Precision **0.404**, Recall **0.651**

Deep Learning provided the highest recall while keeping precision at a reasonable level.



## Final Test Evaluation

The selected Deep Learning model was evaluated on the untouched test set using the previously selected threshold of `0.6`.

Final test performance:

- ROC-AUC: **0.852**
- Precision: **0.347**
- Recall: **0.682**
- F1: **0.460**

Compared with validation results, performance decreased slightly, but the model maintained strong recall and similar overall discrimination.

The final model successfully preserved the recall-focused objective on unseen test data.
