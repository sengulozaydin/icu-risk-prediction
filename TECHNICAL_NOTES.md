# Technical Notes

Operational details for running the existing pipeline. For the project overview, results, and notebook workflow, see the [README](README.md).

## Environment and execution

The project was developed with Python 3.12 on Ubuntu/WSL. [requirements.txt](requirements.txt) lists direct notebook and script dependencies without strict version pins; it is a dependency list rather than a reproducibility lockfile.

Run notebook cells in order. Some exploratory cells rely on earlier in-memory variables, so they are not independent jobs. Full model retraining is computationally expensive, and neural-network results may vary because the saved training code does not fix all random seeds.

## Path configuration

Copy [config.example.toml](config.example.toml) to `config.local.toml` at the repository root and edit `mimic_data_dir`. The local configuration is ignored by Git.

- Relative values resolve against the repository root, regardless of the notebook working directory.
- Absolute paths may point to an existing external dataset; no data needs to be moved or copied.
- Use a path understood by the Python runtime, such as `/mnt/d/datasets/mimic-iii` in WSL or `D:/datasets/mimic-iii` in native Windows Python.
- A leading `~` expands to the current user's home directory.
- Without a local configuration file, the default is `data/raw/mimic-iii-clinical-database-1.4`.
- Restart the notebook kernel after changing the configuration, then run its setup cell again.

[scripts/project_paths.py](scripts/project_paths.py) derives the project root from its own location and supplies the raw-data, `data/processed`, and `reports` paths. Notebook setup searches the current directory and its parents for this module, so the kernel must start in the repository or a subdirectory. There is no need to edit individual notebook paths to compensate for nested folders.

Both flat `TABLE.csv` and nested `TABLE.csv/TABLE.csv` raw-data layouts are supported. Processed files remain in the repository-local `data/processed` directory. Saved notebook outputs are historical and may show paths from the original run; execution uses the shared configuration.

## Advanced vital-event extraction

[scripts/extract_vitals.py](scripts/extract_vitals.py) reads the literal `vital_itemids` mapping saved in [engineering notebook 02](notebooks/data_engineering/02_lab_vital_features.ipynb). Save that notebook before invoking the extractor.

For resource-constrained environments, run with numerical-library thread limits:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/extract_vitals.py
```

These environment variables limit OpenBLAS and OpenMP threads for this command. The extractor itself uses strict, single-threaded PyArrow CSV parsing in small blocks and writes filtered batches incrementally.

### Partial files and malformed CSV input

Extraction writes an incomplete result with a `.partial` suffix. The completed event Parquet replaces the final output only after successful parsing and row-count validation. A malformed CSV raises an error rather than silently skipping a row; a failed run may leave a partial file. Rerunning starts that partial output again rather than resuming it. A parsing failure does not replace an existing completed event Parquet.

### Extraction JSON and cache reuse

The local `data/processed/vitals_first24h.json` report records input signatures, the selected ITEMID mapping, extraction counts, and timing. Input signatures use source file sizes and modification timestamps. When the signature matches and the cached event Parquet has the recorded row count, the extractor reuses the completed cache.

This is a metadata-based cache check, not a full content-hash comparison of raw files.

### Cache regeneration

To force regeneration, remove only the local extraction report `data/processed/vitals_first24h.json`, then rerun the extractor. This prevents the cache-reuse branch from being taken. Keep the raw source data available and do not confuse this report with `vitals_validation.json`, which is produced by the independent validation script.

## Validation and tests

After extraction, run the independent bounded-batch validator:

```bash
python scripts/validate_vitals.py
```

[scripts/validate_vitals.py](scripts/validate_vitals.py) checks identifier matching, the first-24-hour boundaries, selected ITEMIDs, row counts, and cohort coverage. It records retained null/error counts and writes the local `data/processed/vitals_validation.json` summary.

The following tests use synthetic inputs and do not require MIMIC-III data:

```bash
python scripts/test_extract_vitals.py
python scripts/test_project_paths.py
```

- [Extraction test](scripts/test_extract_vitals.py): admission-time inclusion, exclusion at exactly 24 hours, identifier matching, adult/length-of-stay cohort eligibility, preservation of missing measurements, cache reuse, and malformed-input handling without replacing a completed output.
- [Path tests](scripts/test_project_paths.py): default, relative, absolute, and home-directory configuration; invalid configuration values; flat/nested CSV layouts; notebook syntax; and setup from the repository root and notebook folders. They also verify a clear error when the notebook starts outside the repository.

These checks validate extraction and path behavior; they do not retrain models or reproduce the reported performance metrics.
