# ICU Risk Prediction

MIMIC-III hospital mortality prediction using the first 24 hours of adult ICU stays.

## Vital-event extraction

From the project root, run in the existing WSL virtual environment:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/extract_vitals.py
.venv/bin/python scripts/validate_vitals.py
```

Alternatively, run `notebooks/02_feature_engineering.ipynb`. Save changes to its literal `vital_itemids` dictionary before extraction: the extractor reads that saved dictionary. Historical all-item frequency exploration is disabled by default because it scans the entire CSV and retains large Python sets.

The raw-data location is configured by `DATA` in `scripts/extract_vitals.py`. Both flat CSV files and the existing nested `TABLE.csv/TABLE.csv` layout are supported. Only pandas and PyArrow from the existing requirements are needed.

The cohort follows notebook 01: age at ICU entry >= 18, LOS >= 1 day and nonmissing OUTTIME. All 45,253 target stays are retained in the cohort output, including the 627 without selected lab features. Events must match SUBJECT_ID, HADM_ID and ICUSTAY_ID, and satisfy `INTIME <= CHARTTIME < INTIME + 24 hours`.

The CSV is parsed strictly in 1 MiB blocks with a single parsing thread. Selected batches are filtered and written incrementally, without concatenating the raw data or output into memory. Malformed CSV rows cause an error instead of silent data loss. A failed run can leave a `.partial` file; rerunning starts again and replaces that partial file. The completed Parquet is published only after successful parsing and row-count validation.

Outputs under `data/processed/`:

- `vitals_first24h.parquet`: selected measurement events, with original units, null numeric values, STORETIME and ERROR flags retained. Temperature conversion, invalid-measurement removal and aggregation are separate later steps.
- `adult_icu_cohort_first24h.parquet`: all target stays with admission timestamps, for later left joins.
- `vitals_first24h.json`: input signatures, extraction counts and timing. Unchanged inputs and ITEMIDs reuse the completed cache.
- `vitals_validation.json`: results from independent bounded-batch validation.

To force regeneration, remove only the extraction JSON report before rerunning. Do not load the complete event Parquet just to inspect it; use `pyarrow.parquet.ParquetFile(...).iter_batches()` or filtered column reads.

## Diagnosis and verification

The supplied notebook saved a `ModuleNotFoundError` for DuckDB, but no traceback for the reported pandas `IndexError`. The exact original pandas failure therefore remains unconfirmed. A strict PyArrow trial failed with an OS memory-allocation error; WSL had approximately 731 MiB available and an existing Python process held about 4.2 GiB. Single-threaded reading through a buffered Python file and 1 MiB blocks avoids that observed allocation failure. The original notebook's all-item set accumulation also adds memory pressure.

Run the synthetic boundary and failure test with:

```bash
.venv/bin/python scripts/test_extract_vitals.py
```

It checks admission-time inclusion, exclusion at exactly 24 hours, identifier matching, adult/LOS cohort filtering, preservation of missing measurements, cache reuse, and failure on malformed CSV without replacing a completed output.

The laboratory pipeline and existing lab Parquet are not rewritten by this extraction.

## Verified extraction result

The full 35.3 GB CSV was parsed successfully: 330,712,483 source rows, 31,432,046 selected-ITEMID rows, and 7,031,935 first-24-hour output rows. Extraction took 937.8 seconds. Independent batch validation passed for every output row, and a second invocation reused the cache successfully.

The 157,719,470-byte Parquet covers 44,549 of 45,253 target stays. The remaining 704 stays remain in the cohort table. There are 362 stays with selected vital events but no lab-feature row. Raw output retains 5,413 missing numeric values and 2,258 ERROR=1 rows for explicit downstream cleaning.
