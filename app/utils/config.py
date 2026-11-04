from pathlib import Path
from app.utils.constants import BASE_DIR, TEMPLATES_FILE, VALIDATION_DATASET_FILE
import os

def get_template_file() -> Path:
    configured_path = os.getenv("TEMPLATE_DATA_FILE")
    if not configured_path:
        return TEMPLATES_FILE
    dataset_path = Path(configured_path)
    return dataset_path if dataset_path.is_absolute() else BASE_DIR / dataset_path

def get_validation_dataset_file() -> Path:
    configured_path = os.getenv("VALIDATION_DATA_FILE")
    if not configured_path:
        return VALIDATION_DATASET_FILE
    dataset_path = Path(configured_path)
    return dataset_path if dataset_path.is_absolute() else BASE_DIR / dataset_path
