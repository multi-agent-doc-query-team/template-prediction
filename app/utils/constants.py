from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
UNIT_CONVERSION_DIR = DATA_DIR / "unit_conversion"

TEMPLATES_FILE = DATA_DIR / "templates.json"
VALIDATION_DATASET_FILE = DATA_DIR / "dataset.csv"
VECTORIZER_FILE = MODELS_DIR / "vectorizer.joblib"
TEMPLATE_MODEL_FILE = MODELS_DIR / "template_model.joblib"
UNIT_CATALOG_FILE = UNIT_CONVERSION_DIR / "unit_catalog.json"
