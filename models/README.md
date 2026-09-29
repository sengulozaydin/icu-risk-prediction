# Streamlit inference artifacts

- `final_model.keras`: 64 → 32 → 1 network, refitted only on the existing training split with notebook 09's Adam, binary cross-entropy, balanced class weights, 8 epochs and batch size 64.
- `preprocessor.joblib`: fitted `ColumnTransformer`, including numeric median imputer, StandardScaler and categorical OneHotEncoder (`handle_unknown="ignore"`). Load only this trusted repository artifact.
- `feature_schema.json`: ordered 83 raw predictors, numeric/categorical/binary feature lists, categorical vocabulary, ordered encoded features and fixed threshold 0.6.
- `manifest.json`: artifact SHA-256 checksums, package versions, provenance, fixed settings and the original notebook's recorded test metrics.

No original saved weights were available. These weights are a **demo refit**, not the exact weights that produced the recorded ROC-AUC 0.852, recall 0.682, precision 0.347 and F1 0.460. The original final notebook did not set a TensorFlow seed; export uses seed 42 for reproducibility. No threshold search, test-set evaluation or performance optimization is performed. Notebooks and their recorded results are unchanged.

The bundle contains model parameters, aggregate fitted preprocessing statistics and feature metadata only. It contains no patient rows, identifiers, raw data, training history or sample records. Deployment requires no MIMIC files, credentials or local configuration.

To reproduce locally with authorized access to the existing `data/processed/ml_train.parquet`, install `requirements-notebooks.txt`, deliberately remove the previous reviewed bundle, then run `python scripts/export_streamlit_artifacts.py`. Export refuses to overwrite an existing manifest. Review the new bundle and run `python -m unittest discover -s tests` before publishing it. Retraining can change predictions; it must not be represented as reproducing the original test metrics.
