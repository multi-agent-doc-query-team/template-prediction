from fastapi import APIRouter, HTTPException

from app.schemas.telemetry import (
    ConvertTelemetryRequest,
    ConvertedTelemetryReading,
    UnitMetadata,
)
from app.services.unit_conversion_service import (
    convert_readings,
    get_unit_metadata,
)


router = APIRouter(prefix="/api/v1", tags=["Telemetry"])


@router.get("/units/{sensor}", response_model=UnitMetadata)
def get_sensor_units(sensor: str):
    try:
        return get_unit_metadata(sensor)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/telemetry/convert",
    response_model=list[ConvertedTelemetryReading],
)
def convert_telemetry(request: ConvertTelemetryRequest):
    try:
        return convert_readings(
            [reading.model_dump() for reading in request.readings]
        )
    except (KeyError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
