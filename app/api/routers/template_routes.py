from fastapi import APIRouter
from app.api.schemas.template import (
    ClassificationResponse,
    HealthResponse,
    TemplateRequest,
)
from app.api.services.template_service import (
    classify_template as classify,
    get_application_info,
    get_template_health,
)

router = APIRouter()

@router.get("/", tags=["System"])
def root():
    return get_application_info()

@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
)
def health_check():
    return get_template_health()

@router.post(
    "/templates/classify",
    response_model=ClassificationResponse,
    tags=["Template Classification"],
)
def classify_template(request: TemplateRequest):
    return classify(request)
