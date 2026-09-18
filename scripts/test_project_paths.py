"""Verify path configuration and notebook startup without loading clinical data."""
import ast
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from project_paths import PROJECT_ROOT, PROCESSED_DIR, load_raw_data_dir, mimic_csv


class ProjectPathsTest(unittest.TestCase):
    def test_default_relative_absolute_and_home_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config.local.toml"
            expected = root / "data/raw/mimic-iii-clinical-database-1.4"
            self.assertEqual(load_raw_data_dir(config, root), expected)
            config.write_text('mimic_data_dir = "external/raw"\n')
            self.assertEqual(load_raw_data_dir(config, root), root / "external/raw")
            absolute = (root / "external source").as_posix()
            config.write_text(f'mimic_data_dir = "{absolute}"\n')
            self.assertEqual(load_raw_data_dir(config, root), root / "external source")
            config.write_text('mimic_data_dir = "~/clinical-data"\n')
            self.assertEqual(load_raw_data_dir(config, root), Path.home() / "clinical-data")

    def test_invalid_configuration_fails_instead_of_using_another_dataset(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.local.toml"
            for value in ['""', '12']:
                config.write_text(f'mimic_data_dir = {value}\n')
                with self.assertRaises(ValueError):
                    load_raw_data_dir(config, Path(directory))

    def test_flat_and_nested_tables(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flat = root / "PATIENTS.csv"
            flat.write_text("SUBJECT_ID\n1\n")
            nested = root / "ICUSTAYS.csv" / "ICUSTAYS.csv"
            nested.parent.mkdir()
            nested.write_text("ICUSTAY_ID\n1\n")
            self.assertEqual(mimic_csv("PATIENTS", root), flat)
            self.assertEqual(mimic_csv("ICUSTAYS", root), nested)

    def test_notebooks_compile_and_bootstrap_from_each_supported_directory(self):
        notebooks = sorted((PROJECT_ROOT / "notebooks").rglob("*.ipynb"))
        original_cwd = Path.cwd()
        count = 0
        try:
            for notebook in notebooks:
                cells = json.loads(notebook.read_text(encoding="utf-8"))["cells"]
                for index, cell in enumerate(cells):
                    if cell["cell_type"] == "code":
                        compile("".join(cell["source"]), f"{notebook.name}:{index}", "exec")
                if cells[0].get("id") != "shared-project-paths":
                    continue
                count += 1
                for cwd in [PROJECT_ROOT, PROJECT_ROOT / "notebooks", notebook.parent]:
                    os.chdir(cwd)
                    namespace = {}
                    with patch.object(sys, "path", sys.path.copy()):
                        exec("".join(cells[0]["source"]), namespace)
                    self.assertEqual(namespace["PROJECT_ROOT"], PROJECT_ROOT)
                    self.assertEqual(namespace["PROCESSED_DIR"], PROCESSED_DIR)
                with tempfile.TemporaryDirectory() as outside:
                    os.chdir(outside)
                    with self.assertRaisesRegex(RuntimeError, "repository"):
                        exec("".join(cells[0]["source"]), {})
                    os.chdir(original_cwd)
        finally:
            os.chdir(original_cwd)
        self.assertEqual(count, 14)


if __name__ == "__main__":
    unittest.main()
