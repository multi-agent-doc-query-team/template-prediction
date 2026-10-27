from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.services.errors import ConversionBatchError
from app.utils.debug import get_logger
logger = get_logger(__name__)

async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    errors = []
    for error in exc.errors():
        location = error.get("loc", [])
        field = location[-1] if location else "input"
        field_names = {
            "readings": "Readings",
            "sensor": "Sensor",
            "mnemonic": "Mnemonic",
            "unit_type": "Unit Type",
            "value": "Value",
            "source_unit": "Source Unit",
        }
        friendly_name = field_names.get(field, "Input")
        error_type = error.get("type", "")
        if error_type == "missing":
            message = f"Please provide {friendly_name}."
        elif (
            error_type == "too_long"
            and list(location) == ["body", "readings"]
            and isinstance(error.get("input"), list)
        ):
            limit = error["ctx"]["max_length"]
            count = len(error["input"])
            message = (
                f"A maximum of {limit} readings is allowed per request. "
                f"Received {count}."
            )
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

async def http_exception_handler(
    request: Request,
    exc: HTTPException
):
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": "The request could not be completed."
        }
    )

async def unexpected_exception_handler(
    request: Request,
    exc: Exception
):
    logger.error("Unhandled request failure: %s %s", request.method, request.url.path,
                 exc_info=(type(exc), exc, exc.__traceback__))
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

async def conversion_exception_handler(request: Request, exc: ConversionBatchError):
    return JSONResponse(
        status_code=422,
        content={"success": False, "message": str(exc), "errors": exc.errors},
    )

def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(ConversionBatchError, conversion_exception_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)
