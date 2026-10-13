from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
)


TelemetryValue = StrictInt | StrictFloat | StrictStr


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
    "rad",
    "rad/s",
    "Pa·s",
    "V",
    "A",
    "Ω",
    "F",
    "lx",
    "1",
]


class TelemetryReading(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sensor: str = Field(
        alias="Mnemonic",
        min_length=1,
    )

    value: TelemetryValue

    source_unit: str | None = None

    unit_type: str | None = None


class ConvertTelemetryRequest(BaseModel):
    readings: list[TelemetryReading] = Field(
        min_length=1,
    )


class UnitDecision(BaseModel):
    reading_type: ReadingType
    unit_type: str | None = None


class UnitInterpretationBatch(BaseModel):
    decisions: list[UnitDecision]


class ConvertedTelemetryReading(BaseModel):
    sensor: str
    target_unit: SIUnit | None = None
    unit_type: str | None = None
    conversion: str | None = None


class ConvertTelemetryResponse(BaseModel):
    converted_values: list[ConvertedTelemetryReading]