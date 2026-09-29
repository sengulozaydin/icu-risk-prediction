"""Export inference-only artifacts using notebook 09's fixed final configuration.

Reads only the existing local training split; never reads/evaluates the test set.
Run from any directory: python scripts/export_streamlit_artifacts.py
"""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os

os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "2")
os.environ.setdefault("TF_NUM_INTEROP_THREADS", "2")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.class_weight import compute_class_weight

ROOT = Path(__file__).resolve().parents[1]
CATEGORICAL = ["gender", "admission_type", "admission_location"]


def main():
    destination = ROOT / "models"
    if (destination / "manifest.json").exists():
        raise SystemExit("Artifacts already exist. Explicitly remove the reviewed bundle before re-exporting.")
    train = pd.read_parquet(ROOT / "data/processed/ml_train.parquet")
    X = train.drop(columns=["SUBJECT_ID", "HOSPITAL_EXPIRE_FLAG"])
    y = train["HOSPITAL_EXPIRE_FLAG"]
    assert X.shape[1] == 83 and len(X) == 36169
    assert not {"SUBJECT_ID", "ICUSTAY_ID", "HOSPITAL_EXPIRE_FLAG"} & set(X.columns)
    numeric = X.columns.difference(CATEGORICAL).tolist()
    preprocessor = ColumnTransformer([
        ("numeric", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]), numeric),
        ("categorical", Pipeline([
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]), CATEGORICAL),
    ])
    transformed = preprocessor.fit_transform(X)
    weights = compute_class_weight(class_weight="balanced", classes=np.array([0, 1]), y=y)
    # Notebook 09 has no seed. This seed makes the export reproducible without tuning.
    tf.keras.utils.set_random_seed(42)
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(transformed.shape[1],)),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    model.fit(transformed, y, epochs=8, batch_size=64,
              class_weight={0: weights[0], 1: weights[1]}, verbose=2)
    destination.mkdir(exist_ok=True)
    model.save(destination / "final_model.keras")
    joblib.dump(preprocessor, destination / "preprocessor.joblib", compress=3)
    encoder = preprocessor.named_transformers_["categorical"].named_steps["encoder"]
    schema = {
        "features": X.columns.tolist(),
        "numeric_features": numeric,
        "categorical_features": CATEGORICAL,
        "categories": {c: values.tolist() for c, values in zip(CATEGORICAL, encoder.categories_)},
        "binary_features": [c for c in numeric if c.endswith("_present") or c in ["lab_missing", "vital_missing"]],
        "transformed_features": preprocessor.get_feature_names_out().tolist(),
        "threshold": 0.6,
    }
    (destination / "feature_schema.json").write_text(json.dumps(schema, indent=2) + "\n")
    # Only synthetic inputs are used to verify serialization; no patient examples are saved.
    synthetic = pd.DataFrame([{c: (schema["categories"][c][0] if c in CATEGORICAL else np.nan)
                               for c in schema["features"]}])
    before = model(preprocessor.transform(synthetic), training=False).numpy()
    loaded = tf.keras.models.load_model(destination / "final_model.keras", compile=False)
    after = loaded(joblib.load(destination / "preprocessor.joblib").transform(synthetic), training=False).numpy()
    np.testing.assert_allclose(before, after, rtol=1e-6, atol=1e-7)
    manifest = {
        "source_notebook": "notebooks/modeling/09_final_test_evaluation.ipynb",
        "provenance": "Demo refit with original final settings; original notebook weights were not saved. Recorded notebook metrics are not measurements of this refit.",
        "architecture": [64, 32, 1], "epochs": 8, "batch_size": 64,
        "class_weight": "balanced", "export_seed": 42, "threshold": 0.6,
        "recorded_notebook_test_metrics": {"ROC-AUC": 0.852, "Recall": 0.682, "Precision": 0.347, "F1": 0.460},
        "versions": {p: importlib.metadata.version(p) for p in ["tensorflow", "keras", "scikit-learn", "numpy", "pandas", "joblib"]},
        "sha256": {name: hashlib.sha256((destination / name).read_bytes()).hexdigest()
                   for name in ["final_model.keras", "preprocessor.joblib", "feature_schema.json"]},
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Exported model, fitted preprocessing, ordered schema and provenance; no test evaluation performed.")


if __name__ == "__main__":
    main()
