from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TelemetryValue = int | float | str

ReadingType = Literal[
    "physical",
    "dimensionless",
    "text",
    "unknown",
]

SIUnit = Literal[
    "m",
    "m²",
    "m³",
    "m/s",
    "m/s²",
    "kg",
    "kg/m³",
    "s",
    "K",
    "Pa",
    "N",
    "N·m",
    "J",
    "W",
    "m³/s",
    "Hz",
    "rad/s",
    "1",
]


class TelemetryReading(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sensor: str = Field(alias="Mnemonic", min_length=1)
    value: TelemetryValue
    unit: str | None = None
    unit_type: str | None = None


class ConvertTelemetryRequest(BaseModel):
    readings: list[TelemetryReading] = Field(min_length=1)


class UnitInterpretation(BaseModel):
    reading_type: ReadingType
    unit_type: str | None = None
    si_unit: SIUnit | None = None


class ConvertedTelemetryReading(BaseModel):
    sensor: str
    value: TelemetryValue
    unit: str | None = None


class ConvertTelemetryResponse(BaseModel):
    converted_values: list[ConvertedTelemetryReading]