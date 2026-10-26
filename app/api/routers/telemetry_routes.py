from fastapi import APIRouter
from app.schemas.telemetry import ConversionRequest, ConversionResponse
from app.services.unit_conversion_service import convert_readings, health

router = APIRouter(prefix="/api/v1/telemetry", tags=["Telemetry"])

@router.get("/health")
def conversion_health():
    return health()

@router.post("/convert", response_model=ConversionResponse)
def convert_telemetry(request: ConversionRequest):
    return convert_readings(request)
