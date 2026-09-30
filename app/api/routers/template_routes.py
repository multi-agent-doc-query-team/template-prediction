from fastapi import APIRouter, HTTPException

from app.schemas.template import (
    ClassificationResponse,
    HealthResponse,
    TemplateRequest,
)
from app.services.template_service import classify_and_get_template


router = APIRouter()


@router.get("/", tags=["System"])
def root():
    return {
        "success": True,
        "message": "AI Monitoring Template Selection API is running.",
        "version": "1.0.0",
        "documentation": "/docs",
    }


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
)
def health_check():
    return {
        "status": "healthy",
        "message": "Template Selection API is operational.",
    }


@router.post(
    "/api/v1/templates/classify",
    response_model=ClassificationResponse,
    tags=["Template Classification"],
)
def classify_template(request: TemplateRequest):
    try:
        result, error = classify_and_get_template(
            activity_name=request.activity_name,
            well_name=request.well_name,
            service_provider=request.service_provider,
        )

        if error:
            raise HTTPException(
                status_code=error["status_code"],
                detail={
                    "success": False,
                    "message": error["message"],
                },
            )

        return {
            "success": True,
            "message": (
                "Monitoring template selected successfully."
                if not result["needs_review"]
                else "Template prediction requires manual review."
            ),
            "input": {
                "activity_name": request.activity_name,
                "well_name": request.well_name,
                "service_provider": request.service_provider,
            },
            "predicted_template_id": result["template_id"],
            "prediction_confidence": result["confidence"],
            "needs_review": result["needs_review"],
            "predicted_template": {
                key: value
                for key, value in result["template"].items()
                if key != "well_names"
            },
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": "We could not process your request.",
            },
        )
