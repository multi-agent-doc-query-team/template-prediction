from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routers.template_routes import router as template_router


# FASTAPI APPLICATION

app = FastAPI(
    title="AI Monitoring Template Selection API",
    description=(
        "API for selecting the appropriate monitoring template "
        "using Activity Name, Well Name and Service Provider. "
        "The current version uses temporary prediction logic. "
        "The prediction layer will later be replaced by the "
        "final trained classification model."
    ),
    version="1.0.0"
)


# REQUEST VALIDATION ERROR HANDLER - Missing fields, Empty fields, Wrong data types, Invalid field lengths
# Raw FastAPI/Pydantic validation messages are NOT returned

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    errors = []

    for error in exc.errors():

        location = error.get("loc", [])
        field = location[-1] if location else "input"

        # Convert technical field names into readable names
        field_names = {
            "activity_name": "Activity Name",
            "well_name": "Well Name",
            "service_provider": "Service Provider"
        }

        friendly_name = field_names.get(field, "Input")

        error_type = error.get("type", "")

        # Missing field
        if error_type == "missing":
            message = f"Please provide {friendly_name}."

        # Any other invalid value
        else:
            message = f"Please enter a valid {friendly_name}."

        errors.append({
            "field": field,
            "message": message
        })

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Please correct the provided information.",
            "errors": errors
        }
    )


# HTTP EXCEPTION HANDLER
# Handles controlled errors raised inside the application. Only messages explicitly defined by us are returned.

@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException
):

    # If the exception already contains our controlled response
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )

    # Fallback response
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": "The request could not be completed."
        }
    )


# UNEXPECTED ERROR HANDLER
# Handles unexpected internal errors.
#
# IMPORTANT:
# Actual Python/server/file/model errors are NOT sent
# to the API consumer.

@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request,
    exc: Exception
):

    # Later, the actual exception can be logged internally.
    # Never return str(exc) to the API consumer.

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": (
                "We could not process your request at this time. "
                "Please try again later."
            )
        }
    )


app.include_router(template_router)
