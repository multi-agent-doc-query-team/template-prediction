"""Runtime configuration shared by the dataset and prediction layers."""

import os
from pathlib import Path


# config.py lives in app/utils, so the project root is three levels up.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


def get_template_file() -> Path:
    """Return the configured dataset path, relative to the API root if needed."""

    configured_path = os.getenv("TEMPLATE_DATA_FILE")

    if not configured_path:
        return BASE_DIR / "data" / "templates.json"

    dataset_path = Path(configured_path)
    return dataset_path if dataset_path.is_absolute() else BASE_DIR / dataset_path


def get_validation_dataset_file() -> Path:
    """Return the CSV used for input validation."""

    configured_path = os.getenv("VALIDATION_DATA_FILE")

    if not configured_path:
        return BASE_DIR / "data" / "dataset.csv"

    dataset_path = Path(configured_path)
    return dataset_path if dataset_path.is_absolute() else BASE_DIR / dataset_path
