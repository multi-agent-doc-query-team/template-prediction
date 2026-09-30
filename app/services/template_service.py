import csv
import json
from typing import Dict, List, Optional

from app.utils.config import (
    get_template_file,
    get_validation_dataset_file,
)
from app.utils.normalization import normalize_activity_name, normalize_provider_name
from app.services.tools.predictor import (
    normalize_value,
    predict_template_id,
)


TEMPLATE_FILE = get_template_file()
VALIDATION_FILE = get_validation_dataset_file()


USER_MESSAGES = {
    "INVALID_ACTIVITY": {
        "status_code": 400,
        "field": "activity_name",
        "message": "Please enter a valid activity name.",
    },
    "INVALID_SERVICE_PROVIDER": {
        "status_code": 400,
        "field": "service_provider",
        "message": "Please enter a valid service provider.",
    },
    "INVALID_WELL_NAME": {
        "status_code": 400,
        "field": "well_name",
        "message": "Please enter a valid well name.",
    },
    "PREDICTION_ERROR": {
        "status_code": 500,
        "message": "The monitoring template could not be selected.",
    },
    "TEMPLATE_DATA_NOT_FOUND": {
        "status_code": 500,
        "message": "The selected monitoring template is unavailable.",
    },
}

MIN_PREDICTION_CONFIDENCE = 0.60


def load_templates() -> List[Dict]:
    if not TEMPLATE_FILE.exists():
        raise FileNotFoundError("Template repository file is missing.")

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as file:
        templates = json.load(file)

    if not isinstance(templates, list) or not templates:
        raise ValueError("Invalid templates.json.")

    return templates


def build_template_index() -> Dict[str, Dict]:
    index: Dict[str, Dict] = {}

    for template in load_templates():
        template_id = template.get("template_id")

        if not template_id:
            raise ValueError("Template is missing template_id.")

        if template_id in index:
            raise ValueError(f"Duplicate template ID: {template_id}")

        index[template_id] = template

    return index


TEMPLATE_INDEX = build_template_index()


def validate_catalog_inputs(
    activity_name: str,
    well_name: str,
    service_provider: str,
) -> List[str]:
    """Require the exact provider, activity, and well combination."""

    provider_input = normalize_provider_name(service_provider)
    activity_input = normalize_activity_name(activity_name)
    well_input = normalize_value(well_name)

    provider_exists = False
    activity_exists = False
    well_exists = False
    exact_combination_exists = False

    with open(
        VALIDATION_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            provider = normalize_provider_name(row.get("service_provider", ""))
            activity = normalize_activity_name(row.get("activity", ""))
            well = normalize_value(
                row.get("well_name", "")
            )

            if provider == provider_input:
                provider_exists = True

            if activity == activity_input:
                activity_exists = True

            if well == well_input:
                well_exists = True

            if (
                provider == provider_input
                and activity == activity_input
                and well == well_input
            ):
                exact_combination_exists = True

    errors: List[str] = []

    if not provider_exists:
        errors.append("INVALID_SERVICE_PROVIDER")

    if not activity_exists:
        errors.append("INVALID_ACTIVITY")

    if not well_exists:
        errors.append("INVALID_WELL_NAME")

    if (
        provider_exists
        and activity_exists
        and well_exists
        and not exact_combination_exists
    ):
        errors.append("INVALID_WELL_NAME")

    return errors


def get_expected_template_id(
    activity_name: str,
    well_name: str,
    service_provider: str,
) -> Optional[str]:
    """Return the dataset label for an already validated combination."""

    provider_input = normalize_provider_name(service_provider)
    activity_input = normalize_activity_name(activity_name)
    well_input = normalize_value(well_name)

    with open(VALIDATION_FILE, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if (
                normalize_provider_name(row.get("service_provider", ""))
                == provider_input
                and normalize_activity_name(row.get("activity", ""))
                == activity_input
                and normalize_value(row.get("well_name", "")) == well_input
            ):
                return row.get("template_id") or None

    return None


def build_validation_error(
    error_codes: List[str],
) -> Optional[Dict]:
    errors = []

    for code in error_codes:
        error_response = USER_MESSAGES.get(code)

        if error_response:
            errors.append(
                {
                    "code": code,
                    "field": error_response["field"],
                    "message": error_response["message"],
                }
            )

    if not errors:
        return None

    return {
        "status_code": 400,
        "message": errors[0]["message"],
        "errors": errors,
    }


def get_template_by_id(
    template_id: str,
) -> Optional[Dict]:
    return TEMPLATE_INDEX.get(template_id)


def classify_and_get_template(
    activity_name: str,
    well_name: str,
    service_provider: str,
):
    validation_codes = validate_catalog_inputs(
        activity_name=activity_name,
        well_name=well_name,
        service_provider=service_provider,
    )

    validation_error = build_validation_error(validation_codes)

    if validation_error:
        return None, validation_error

    expected_template_id = get_expected_template_id(
        activity_name=activity_name,
        well_name=well_name,
        service_provider=service_provider,
    )

    try:
        template_id, prediction_errors, confidence = predict_template_id(
            activity_name=activity_name,
            well_name=well_name,
            service_provider=service_provider,
        )

    except Exception:
        return None, USER_MESSAGES["PREDICTION_ERROR"]

    if prediction_errors:
        prediction_error = build_validation_error(prediction_errors)

        if prediction_error:
            return None, prediction_error

        return None, USER_MESSAGES["PREDICTION_ERROR"]

    if not template_id:
        return None, USER_MESSAGES["PREDICTION_ERROR"]

    template = get_template_by_id(template_id)

    if template is None:
        return None, USER_MESSAGES["TEMPLATE_DATA_NOT_FOUND"]

    return {
        "template_id": template_id,
        "template": template,
        "confidence": confidence,
        "expected_template_id": expected_template_id,
        "prediction_matches_dataset": (
            expected_template_id is not None
            and template_id == expected_template_id
        ),
        "needs_review": (
            confidence is None
            or confidence < MIN_PREDICTION_CONFIDENCE
            or template_id != expected_template_id
        ),
    }, None
