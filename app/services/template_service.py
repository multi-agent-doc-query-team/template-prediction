import json
from typing import Dict, List, Optional

from app.utils.config import get_template_file
from app.services.tools.predictor import (
    load_validation_catalog,
    normalize_value,
    predict_template_id,
)


# TEMPLATE FILE LOCATION

TEMPLATE_FILE = get_template_file()


# USER-FRIENDLY ERROR MESSAGES


USER_MESSAGES = {

    "INVALID_ACTIVITY": {
        "status_code": 400,
        "field": "activity_name",
        "message": "Please enter a valid activity name."
    },

    "INVALID_SERVICE_PROVIDER": {
        "status_code": 400,
        "field": "service_provider",
        "message": "Please enter a valid service provider."
    },

    "INVALID_WELL_NAME": {
        "status_code": 400,
        "field": "well_name",
        "message": "Please enter a valid well name."
    },

    "TEMPLATE_NOT_FOUND": {
        "status_code": 404,
        "message": (
            "No suitable monitoring template was found "
            "for the provided details."
        )
    },

    "TEMPLATE_DATA_NOT_FOUND": {
        "status_code": 500,
        "message": (
            "The selected monitoring template is currently unavailable. "
            "Please try again later."
        )
    },

    "PREDICTION_ERROR": {
        "status_code": 500,
        "message": (
            "The monitoring template could not be selected at this time. "
            "Please try again later."
        )
    }
}


# LOAD TEMPLATE REPOSITORY

def load_templates() -> List[Dict]:
    """
    Load all monitoring templates from templates.json.

    Any technical error raised here will be handled internally
    by the application's global exception handler.
    Technical details will not be returned to the API consumer.
    """

    if not TEMPLATE_FILE.exists():
        raise FileNotFoundError(
            "Template repository file is missing."
        )

    try:
        with open(
            TEMPLATE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            templates = json.load(file)

    except json.JSONDecodeError as exc:
        raise ValueError(
            "Template repository contains invalid JSON."
        ) from exc

    if not isinstance(templates, list):
        raise ValueError(
            "Template repository has an invalid structure."
        )

    if not templates:
        raise ValueError(
            "Template repository is empty."
        )

    return templates


# BUILD TEMPLATE INDEX

def build_template_index() -> Dict[str, Dict]:
    """
    Create a dictionary where:

        key   = template_id
        value = complete template

    This allows fast retrieval of a template after
    classification.
    """

    templates = load_templates()

    template_index = {}

    for template in templates:

        # Make sure every template is a JSON object
        if not isinstance(template, dict):
            raise ValueError(
                "Invalid template found in template repository."
            )

        template_id = template.get("template_id")
        well_names = template.get("well_names", [])

        # Every template must contain template_id
        if not template_id:
            raise ValueError(
                "A template is missing its template_id."
            )

        if (
            not isinstance(well_names, list)
            or not all(isinstance(well_name, str) for well_name in well_names)
        ):
            raise ValueError(
                "A template has an invalid well_names value."
            )

        # Duplicate IDs should not exist
        if template_id in template_index:
            raise ValueError(
                "Duplicate template_id found in template repository."
            )

        template_index[template_id] = template

    return template_index


# LOAD TEMPLATE INDEX ON APPLICATION STARTUP

TEMPLATE_INDEX = build_template_index()

# Input validity comes from every row of the labelled CSV dataset.  The
# template JSON remains the repository for the selected template's details.
VALIDATION_CATALOG = load_validation_catalog()


def validate_catalog_inputs(
    activity_name: str,
    well_name: str,
    service_provider: str
) -> List[str]:
    """Validate every input against the configured labelled CSV dataset."""

    errors = []

    if normalize_value(service_provider) not in VALIDATION_CATALOG.providers:
        errors.append("INVALID_SERVICE_PROVIDER")

    if normalize_value(activity_name) not in VALIDATION_CATALOG.activities:
        errors.append("INVALID_ACTIVITY")

    if normalize_value(well_name) not in VALIDATION_CATALOG.well_names:
        errors.append("INVALID_WELL_NAME")

    return errors


def build_validation_error(error_codes: List[str]) -> Optional[Dict]:
    """Convert internal validation codes into one safe API response."""

    errors = []

    for error_code in error_codes:
        error_response = USER_MESSAGES.get(error_code)

        if not error_response or error_response["status_code"] != 400:
            return None

        errors.append({
            "code": error_code,
            "field": error_response["field"],
            "message": error_response["message"]
        })

    if not errors:
        return None

    message = (
        errors[0]["message"]
        if len(errors) == 1
        else "Please correct the invalid input values."
    )

    return {
        "status_code": 400,
        "message": message,
        "errors": errors
    }


# TEMPLATE RETRIEVAL

def get_template_by_id(
    template_id: str
) -> Optional[Dict]:
    """
    Retrieve the complete monitoring template using
    the predicted template_id.
    """

    return TEMPLATE_INDEX.get(template_id)


# CLASSIFICATION + TEMPLATE RETRIEVAL SERVICE

def classify_and_get_template(
    activity_name: str,
    well_name: str,
    service_provider: str
):
    """
    Complete template-selection flow.

    Flow:

        Activity Name
        Well Name
        Service Provider
                |
                v
        Prediction Function
                |
                v
          Template ID
                |
                v
        Template Repository
                |
                v
         Complete Template

    Currently predict_template_id() uses temporary dummy
    prediction logic.

    Later, only the prediction function needs to be replaced
    by the selected ML classification model.
    """

    # STEP 1: VALIDATE AGAINST THE CURRENT CATALOGUE

    catalog_validation_codes = validate_catalog_inputs(
        activity_name=activity_name,
        well_name=well_name,
        service_provider=service_provider
    )


    # STEP 2: GET TEMPLATE PREDICTION

    try:

        template_id, prediction_error = predict_template_id(
            activity_name=activity_name,
            well_name=well_name,
            service_provider=service_provider
        )

    except Exception:

        # Do not expose actual prediction/model errors.
        return None, USER_MESSAGES["PREDICTION_ERROR"]


    # STEP 3: HANDLE PREDICTION ERRORS

    if prediction_error:

        # Combine catalogue validation with model/data validation.  The
        # production predictor is still called when catalogue values are
        # invalid so it can report an invalid well name in the same response.
        combined_validation_codes = list(catalog_validation_codes)
        combined_validation_codes.extend(
            error_code
            for error_code in prediction_error
            if USER_MESSAGES.get(error_code, {}).get("status_code") == 400
        )

        validation_error = build_validation_error(
            list(dict.fromkeys(combined_validation_codes))
        )

        if validation_error:
            return None, validation_error

        # prediction_error should contain only internal error codes such as:
        #
        # INVALID_ACTIVITY
        # INVALID_SERVICE_PROVIDER
        # TEMPLATE_NOT_FOUND

        validation_error = build_validation_error(prediction_error)

        if validation_error:
            return None, validation_error

        if len(prediction_error) != 1:
            return None, USER_MESSAGES["PREDICTION_ERROR"]

        error_response = USER_MESSAGES.get(prediction_error[0])

        if error_response:
            return None, error_response

        return None, USER_MESSAGES["PREDICTION_ERROR"]

    validation_error = build_validation_error(catalog_validation_codes)

    if validation_error:
        return None, validation_error


    # STEP 4: VERIFY TEMPLATE ID
    

    if not template_id:

        return None, USER_MESSAGES["PREDICTION_ERROR"]


    # STEP 5: RETRIEVE COMPLETE TEMPLATE

    template = get_template_by_id(template_id)


    # STEP 6: CHECK TEMPLATE EXISTS
    

    if template is None:

        # Do NOT expose the predicted template ID here.
        #
        # Internally we know that the model returned an ID
        # which is missing from templates.json.
        #
        # The API consumer only receives a friendly message.

        return None, USER_MESSAGES["TEMPLATE_DATA_NOT_FOUND"]


    # STEP 7: RETURN SUCCESSFUL RESULT

    return {
        "template_id": template_id,
        "template": template
    }, None
