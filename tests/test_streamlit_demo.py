"""Synthetic-only inference and Streamlit regression checks; no MIMIC access."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from inference import classify, load_bundle, predict


class DemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load_bundle()
        cls.schema = cls.bundle[2]

    def synthetic(self):
        return {f: self.schema["categories"][f][0] if f in self.schema["categories"] else np.nan
                for f in self.schema["features"]}

    def test_saved_pipeline_and_feature_order(self):
        values = self.synthetic()
        values["age"] = 60.0
        values["gender"] = "UNSEEN_CATEGORY"
        probability = predict(values, self.bundle)
        self.assertTrue(0 <= probability <= 1)
        self.assertEqual(probability, predict(dict(reversed(list(values.items()))), self.bundle))
        prep = self.bundle[1]
        transformed = prep.transform(pd.DataFrame([values], columns=self.schema["features"]))
        self.assertTrue(np.isfinite(transformed).all())
        numeric = prep.named_transformers_["numeric"]
        expected = (numeric.named_steps["imputer"].statistics_ - numeric.named_steps["scaler"].mean_) / numeric.named_steps["scaler"].scale_
        age_index = self.schema["numeric_features"].index("age")
        expected[age_index] = (60.0 - numeric.named_steps["scaler"].mean_[age_index]) / numeric.named_steps["scaler"].scale_[age_index]
        np.testing.assert_allclose(transformed[0, :80], expected)
        with self.assertRaises(ValueError):
            predict({"age": 60}, self.bundle)
        values["age"] = np.inf
        with self.assertRaises(ValueError):
            predict(values, self.bundle)

    def test_fixed_threshold_boundary(self):
        self.assertEqual(classify(0.599999), "Below selected risk threshold")
        self.assertEqual(classify(0.6), "At or above selected risk threshold")
        self.assertEqual(classify(1), "At or above selected risk threshold")

    def test_integrity_and_missing_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "models"
            shutil.copytree(ROOT / "models", target)
            schema = target / "feature_schema.json"
            schema.write_text(schema.read_text() + " ")
            with self.assertRaisesRegex(ValueError, "integrity"):
                load_bundle(target)
            schema.unlink()
            with self.assertRaises(FileNotFoundError):
                load_bundle(target)

    def test_ui_without_dataset(self):
        # Run the deployment files from a standalone directory with no data/config/scripts.
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for name in ["app.py", "inference.py"]:
                shutil.copy2(ROOT / name, target / name)
            shutil.copytree(ROOT / "models", target / "models")
            self.assertFalse((target / "data").exists())
            probe = """
from pathlib import Path
from streamlit.testing.v1 import AppTest
import inference
assert inference.MODEL_DIR == Path.cwd() / 'models'
app = AppTest.from_file('app.py').run(timeout=60)
assert not app.exception and not app.error
app.button[0].click().run(timeout=60)
assert not app.exception and not app.error
assert any(m.label == 'Estimated mortality probability' for m in app.metric)
"""
            isolated = subprocess.run([sys.executable, "-c", probe], cwd=target,
                                      capture_output=True, text=True, timeout=90)
            self.assertEqual(isolated.returncode, 0, isolated.stderr)
            app = AppTest.from_file(str(target / "app.py")).run(timeout=60)
            self.assertFalse(app.exception)
            self.assertEqual(len(app.number_input) + len(app.selectbox), 83)
            self.assertEqual(len(app.tabs), 5)
            app.button[0].click().run(timeout=60)
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            self.assertTrue(any(m.label == "Estimated mortality probability" for m in app.metric))
            for widget in app.number_input:
                widget.set_value(1.0)
            for widget in app.selectbox:
                if widget.key in self.schema["categories"]:
                    widget.set_value(self.schema["categories"][widget.key][-1])
                else:
                    widget.set_value(1)
            app.button[0].click().run(timeout=60)
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            self.assertTrue(any("Model classification:" in m.value for m in app.markdown))


if __name__ == "__main__":
    unittest.main()
