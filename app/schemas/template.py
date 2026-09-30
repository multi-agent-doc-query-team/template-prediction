from typing import List, Optional

from pydantic import BaseModel, Field


class RequestInput(BaseModel):
    activity_name: str = Field(..., min_length=1)
    well_name: str = Field(..., min_length=1)
    service_provider: str = Field(..., min_length=1)


class TemplateRequest(BaseModel):
    activity_name: str = Field(..., min_length=1)
    well_name: str = Field(..., min_length=1)
    service_provider: str = Field(..., min_length=1)


class TemplateDetails(BaseModel):
    template_id: str
    provider: Optional[str] = None
    activity: Optional[str] = None
    version: Optional[str] = None
    field_group: Optional[str] = None
    required_parameters: List[str] = []


class ClassificationResponse(BaseModel):
    success: bool
    message: str
    input: RequestInput
    predicted_template_id: str
    prediction_confidence: Optional[float] = None
    needs_review: bool = False
    predicted_template: TemplateDetails


class HealthResponse(BaseModel):
    status: str
    message: str
