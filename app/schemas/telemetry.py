from typing import List

from pydantic import BaseModel, Field


class TelemetryReading(BaseModel):
    sensor: str = Field(..., min_length=1)
    value: float
    desired_unit: str = Field(..., min_length=1)


class ConvertTelemetryRequest(BaseModel):
    readings: List[TelemetryReading] = Field(..., min_length=1)


class ConvertedTelemetryReading(BaseModel):
    sensor: str
    value: float
    source_unit: str
    target_unit: str


class UnitMetadata(BaseModel):
    sensor: str
    unit_type: str
    source_unit: str
    target_unit: str
