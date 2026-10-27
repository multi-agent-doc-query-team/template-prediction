from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.exception_handlers import register_exception_handlers
from app.api.routers.telemetry_routes import router as telemetry_router
from app.api.routers.template_routes import router as template_router
from app.repositories.template_repository import get_template_repository
from app.services.tools.predictor import get_predictor
from app.services.unit_conversion_service import get_converter
from app.utils.debug import configure_logging, get_logger
from app.utils.env import load_environment
import os

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing API resources.")
    try:
        logger.debug("Loading unit conversion resources.")
        get_converter()
        logger.debug("Loading template repository and prediction adapter.")
        get_template_repository()
        get_predictor()
        if os.getenv("TEMPLATE_PREDICTOR_MODULE", "app.ml_predictor") == "app.ml_predictor":
            from app.ml_predictor import load_model_bundle
            load_model_bundle()
    except Exception:
        logger.exception("API startup failed.")
        raise
    logger.info("API resources ready.")
    try:
        yield
    finally:
        logger.info("API stopped.")

def create_app() -> FastAPI:
    configure_logging(load_environment())
    app = FastAPI(
        title="AI Monitoring Template Selection API",
        description=(
            "API for selecting the appropriate monitoring template "
            "using Activity Name, Well Name and Service Provider. "
            "Template prediction uses the saved classification model. "
            "Includes live Pint SI conversion formulas and explicit passthrough "
            "handling at /api/v1/telemetry/convert."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )
    register_exception_handlers(app)
    app.include_router(template_router)
    app.include_router(telemetry_router)
    return app
