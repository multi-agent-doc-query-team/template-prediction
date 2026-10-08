from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SIUnit = Literal[
    "m", "m²", "m³", "m/s", "m/s²", "kg", "kg/m³",
    "s", "K", "Pa", "N", "N·m", "J", "W",
    "m³/s", "Hz", "rad/s", "1",
]

TelemetryValue = int | float | str

ReadingType = Literal[
    "physical",
    "dimensionless",
    "text",
    "unknown",
]


class AIReadingInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sensor: str = Field(alias="Mnemonic", min_length=1)
    value: TelemetryValue
    unit: str | None = None
    unit_type: str | None = None


class AIUnitConversionRequest(BaseModel):
    readings: list[AIReadingInput] = Field(min_length=1)


class QwenSingleConversion(BaseModel):
    sensor: str
    reading_type: ReadingType
    value: TelemetryValue
    unit: SIUnit | None


class AIConvertedReading(BaseModel):
    sensor: str
    value: TelemetryValue
    unit: str | None = None


class AIUnitConversionResponse(BaseModel):
    converted_values: list[AIConvertedReading]