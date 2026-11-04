from pydantic import AliasChoices, BaseModel, ConfigDict, Field, StrictFloat, StrictInt, field_validator, model_validator
from app.utils.unit_conversion.aliases import PASSTHROUGH
import math

class Reading(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mnemonic: str = Field(min_length=1, validation_alias=AliasChoices('mnemonic','Mnemonic','sensor'))
    value: StrictInt | StrictFloat | str
    source_unit: str = Field(min_length=1)
    unit_type: str | None = None

    @field_validator('value', mode='before')
    @classmethod
    def validate_number(cls, value):
        if isinstance(value, str):
            if not value.strip():
                raise ValueError('A nonblank value is required.')
            return value
        if type(value) not in (int, float):
            raise ValueError('A numeric value is required.')
        try:
            finite = math.isfinite(value)
        except (OverflowError, ValueError):
            finite = False
        if not finite:
            raise ValueError('A finite numeric value is required.')
        return value

    @model_validator(mode='after')
    def validate_passthrough_string(self):
        if isinstance(self.value, str) and self.source_unit not in PASSTHROUGH:
            raise ValueError('Strings are allowed only for explicit passthrough labels.')
        return self

    @field_validator('mnemonic','source_unit')
    @classmethod
    def clean_required(cls, value):
        if not value.strip(): raise ValueError('Value cannot be blank.')
        return value.strip()

class ConversionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    readings: list[Reading] = Field(min_length=1, max_length=50)

class Formula(BaseModel):
    sensor: str
    target_unit: str
    unit_type: str | None
    multiply: float
    divide: float
    add: float
    subtract: float

class ConversionResponse(BaseModel):
    converted_values: list[Formula]
