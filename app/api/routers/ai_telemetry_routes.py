from fastapi import APIRouter, HTTPException

from app.schemas.ai_telemetry import (
    AIUnitConversionRequest,
    AIUnitConversionResponse,
)
from app.services.ai_unit_conversion_service import (
    AIConversionError,
    AIModelUnavailable,
    convert_readings,
)


router = APIRouter(prefix="/api/v1", tags=["AI Telemetry Conversion"])


@router.post(
    "/telemetry/convert-ai",
    response_model=AIUnitConversionResponse,
    response_model_exclude_none=True,
)
def convert_telemetry_with_ai(
    request: AIUnitConversionRequest,
) -> AIUnitConversionResponse:
    try:
        return convert_readings(request)

    except AIModelUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "message": str(exc),
            },
        ) from exc

    except AIConversionError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "success": False,
                "message": str(exc),
            },
        ) from exc