from typing import Dict, List, Optional
from app.repositories.template_repository import get_template_repository
from app.services.tools.predictor import predict_template_id
import logging

logger = logging.getLogger(__name__)

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

def validate_catalog_inputs(
    activity_name: str,
    well_name: str,
    service_provider: str,
) -> List[str]:
    return get_template_repository().validate(
        activity_name, well_name, service_provider
    )

def get_expected_template_id(
    activity_name: str,
    well_name: str,
    service_provider: str,
) -> Optional[str]:
    return get_template_repository().expected_id(
        activity_name, well_name, service_provider
    )

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

def get_template_by_id(template_id: str) -> Optional[Dict]:
    return get_template_repository().get(template_id)

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
        logger.exception("Template prediction failed.")
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
