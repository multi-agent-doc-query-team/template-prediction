from typing import Annotated, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
)


TelemetryValue = Annotated[
    StrictInt | StrictFloat | StrictStr,
    Field(),
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
]

ReadingType = Literal[
    "physical",
    "dimensionless",
    "text",
    "unknown",
]


class AIReadingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sensor: str = Field(
        min_length=1,
        validation_alias=AliasChoices("sensor", "Mnemonic", "mnemonic"),
    )
    value: TelemetryValue
    unit: str | None = Field(
        default=None,
        validation_alias=AliasChoices("unit", "source_unit"),
    )
    unit_type: str | None = None

    @field_validator("sensor")
    @classmethod
    def clean_sensor(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Sensor name cannot be blank.")
        return value

    @field_validator("unit", "unit_type", mode="before")
    @classmethod
    def normalize_null_text(cls, value):
        if isinstance(value, str) and value.strip().casefold() in {
            "",
            "null",
            "none",
        }:
            return None
        return value


class AIUnitConversionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    readings: list[AIReadingInput] = Field(min_length=1, max_length=50)


class AIConvertedReading(BaseModel):
    sensor: str
    value: TelemetryValue
    unit: SIUnit | None = None


class AIUnitConversionResponse(BaseModel):
    converted_values: list[AIConvertedReading]


class QwenDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reading_index: int = Field(ge=0)
    sensor: str = Field(min_length=1)
    reading_type: ReadingType
    value: TelemetryValue
    unit: SIUnit | None = None


class QwenDecisionBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decisions: list[QwenDecision]