"""Shared repository paths; configure raw data once in config.local.toml."""
from pathlib import Path
import tomllib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
CONFIG_FILE = PROJECT_ROOT / "config.local.toml"


def load_raw_data_dir(config_file=CONFIG_FILE, project_root=PROJECT_ROOT):
    """Resolve relative configuration paths against the repository, never the cwd."""
    config_file = Path(config_file)
    settings = {}
    if config_file.exists():
        with config_file.open("rb") as handle:
            settings = tomllib.load(handle)
    value = settings.get("mimic_data_dir", "data/raw/mimic-iii-clinical-database-1.4")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("mimic_data_dir must be a non-empty path in config.local.toml")
    path = Path(value).expanduser()
    return path if path.is_absolute() else Path(project_root) / path


MIMIC_DATA_DIR = load_raw_data_dir()


def mimic_csv(table, data_dir=None):
    """Support both TABLE.csv and TABLE.csv/TABLE.csv source layouts."""
    folder = MIMIC_DATA_DIR if data_dir is None else Path(data_dir)
    path = folder / (table + ".csv")
    return path if path.is_file() else path / (table + ".csv")
