"""Prediction, catalogue lookup, and input-validation helpers."""

import csv
import importlib
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Dict, FrozenSet, List, Optional, Tuple

from app.utils.config import get_template_file, get_validation_dataset_file


PredictionResult = Tuple[Optional[str], List[str]]
REQUIRED_COLUMNS = {"service_provider", "activity", "well_name"}
TEMPLATE_FILE = get_template_file()


def normalize_value(value: str) -> str:
    """Apply consistent normalization before matching catalogue values."""

    return value.strip().lower().replace("-", "_").replace(" ", "_")


def load_templates() -> List[Dict]:
    """Load the template repository used by the fallback predictor."""

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as file:
        templates = json.load(file)

    if not isinstance(templates, list):
        raise ValueError("Template repository has an invalid structure.")

    return templates


def predict_catalog_template_id(
    activity_name: str,
    well_name: str,
    service_provider: str,
) -> PredictionResult:
    """Select an exact match from the current template dataset."""

    provider = normalize_value(service_provider)
    activity = normalize_value(activity_name)
    well = normalize_value(well_name)

    for template in load_templates():
        template_provider = template.get("provider")
        template_activity = template.get("activity")
        well_names = template.get("well_names", [])

        if (
            isinstance(template_provider, str)
            and isinstance(template_activity, str)
            and isinstance(well_names, list)
            and provider == normalize_value(template_provider)
            and activity == normalize_value(template_activity)
            and well
            in {normalize_value(name) for name in well_names if isinstance(name, str)}
        ):
            return template.get("template_id"), []

    return None, ["TEMPLATE_NOT_FOUND"]


@dataclass(frozen=True)
class ValidationCatalog:
    providers: FrozenSet[str]
    activities: FrozenSet[str]
    well_names: FrozenSet[str]


def load_validation_catalog() -> ValidationCatalog:
    """Build an input-validation catalogue from the labelled CSV dataset."""

    dataset_file: Path = get_validation_dataset_file()

    if not dataset_file.exists():
        raise FileNotFoundError("Validation dataset file is missing.")

    with open(dataset_file, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise ValueError("Validation dataset is missing required columns.")

        providers = set()
        activities = set()
        well_names = set()

        for row in reader:
            provider = row.get("service_provider", "")
            activity = row.get("activity", "")
            well_name = row.get("well_name", "")

            if isinstance(provider, str) and provider.strip():
                providers.add(normalize_value(provider))
            if isinstance(activity, str) and activity.strip():
                activities.add(normalize_value(activity))
            if isinstance(well_name, str) and well_name.strip():
                well_names.add(normalize_value(well_name))

    if not providers or not activities or not well_names:
        raise ValueError("Validation dataset contains no usable input values.")

    return ValidationCatalog(
        providers=frozenset(providers),
        activities=frozenset(activities),
        well_names=frozenset(well_names),
    )


@lru_cache(maxsize=1)
def _load_predictor() -> Callable[..., PredictionResult]:
    """Load an optional production predictor, or use the catalogue fallback."""

    module_name = os.getenv("TEMPLATE_PREDICTOR_MODULE")

    # Both former module paths remain accepted for existing deployments.
    if not module_name or module_name in {
        "app.catalog_predictor",
        "app.prediction.catalog_predictor",
    }:
        return predict_catalog_template_id

    module = importlib.import_module(module_name)
    predictor = getattr(module, "predict_template_id", None)

    if not callable(predictor):
        raise RuntimeError(
            "The configured predictor module must define predict_template_id."
        )

    return predictor


def predict_template_id(
    activity_name: str,
    well_name: str,
    service_provider: str,
) -> PredictionResult:
    """Delegate prediction to the configured model or dataset predictor."""

    return _load_predictor()(
        activity_name=activity_name,
        well_name=well_name,
        service_provider=service_provider,
    )
