from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class TemplateRequest(BaseModel):
    activity_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Current well activity"
    )

    well_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the well"
    )

    service_provider: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Service provider name"
    )

    @field_validator(
        "activity_name",
        "well_name",
        "service_provider",
        mode="before"
    )
    @classmethod
    def validate_text_fields(cls, value):
        if value is None:
            raise ValueError("This field is required.")

        if not isinstance(value, str):
            raise ValueError("Value must be provided as text.")

        value = value.strip()

        if not value:
            raise ValueError(
                "Value cannot be empty or contain only spaces."
            )

        return value


class TemplateDetails(BaseModel):
    template_id: str
    provider: str
    activity: str
    version: str
    field_group: str
    required_parameters: List[str]


class RequestInput(BaseModel):
    activity_name: str
    well_name: str
    service_provider: str


class ClassificationResponse(BaseModel):
    success: bool
    message: str
    input: RequestInput
    predicted_template_id: str
    predicted_template: TemplateDetails


class HealthResponse(BaseModel):
    status: str
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    errors: List[ErrorDetail] = []
