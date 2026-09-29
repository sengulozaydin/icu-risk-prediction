"""Inference uses only the trusted, committed artifact bundle; no dataset access."""
from pathlib import Path
import hashlib
import json
import os

os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "2")
os.environ.setdefault("TF_NUM_INTEROP_THREADS", "2")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf

MODEL_DIR = Path(__file__).resolve().parent / "models"
THRESHOLD = 0.6


def load_bundle(directory=MODEL_DIR):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    for name in ("final_model.keras", "preprocessor.joblib", "feature_schema.json"):
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != manifest["sha256"][name]:
            raise ValueError(f"Artifact integrity check failed: {name}")
    schema = json.loads((directory / "feature_schema.json").read_text())
    # Load only repository-owned files, never user-uploaded pickle/joblib objects.
    preprocessor = joblib.load(directory / "preprocessor.joblib")
    model = tf.keras.models.load_model(directory / "final_model.keras", compile=False)
    if schema["threshold"] != THRESHOLD or manifest["threshold"] != THRESHOLD:
        raise ValueError("The final model threshold must remain 0.6.")
    if list(preprocessor.feature_names_in_) != schema["features"]:
        raise ValueError("Raw feature order does not match fitted preprocessing.")
    if list(preprocessor.get_feature_names_out()) != schema["transformed_features"]:
        raise ValueError("Encoded feature order does not match the schema.")
    if model.input_shape[-1] != len(schema["transformed_features"]):
        raise ValueError("Model input width does not match preprocessing.")
    return model, preprocessor, schema, manifest


def classify(probability):
    return "At or above selected risk threshold" if probability >= THRESHOLD else "Below selected risk threshold"


def predict(values, bundle):
    model, preprocessor, schema, _ = bundle
    if set(values) != set(schema["features"]):
        raise ValueError("Provide exactly the expected 83 predictors.")
    frame = pd.DataFrame([values], columns=schema["features"])
    frame[schema["numeric_features"]] = frame[schema["numeric_features"]].astype(float)
    if np.isinf(frame[schema["numeric_features"]].to_numpy()).any():
        raise ValueError("Numeric inputs must be finite or left blank.")
    transformed = preprocessor.transform(frame)
    probability = float(model(transformed, training=False).numpy().ravel()[0])
    if not np.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("Model returned an invalid probability.")
    return probability
