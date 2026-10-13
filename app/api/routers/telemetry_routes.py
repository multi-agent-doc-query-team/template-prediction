from fastapi import APIRouter, HTTPException

from app.schemas.telemetry import (
    ConvertTelemetryRequest,
    ConvertTelemetryResponse,
)
from app.services.unit_conversion_service import (
    UnitConversionError,
    UnitModelUnavailable,
    convert_readings,
)


router = APIRouter(prefix="/api/v1", tags=["Telemetry"])


@router.post(
    "/telemetry/convert",
    response_model=ConvertTelemetryResponse,
)
def convert_telemetry(
    request: ConvertTelemetryRequest,
) -> ConvertTelemetryResponse:
    try:
        return convert_readings(request)

    except UnitModelUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "message": str(exc),
            },
        ) from exc

    except UnitConversionError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "success": False,
                "message": str(exc),
            },
        ) from exc