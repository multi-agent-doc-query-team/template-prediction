from functools import lru_cache
from typing import Callable, List, Optional, Tuple
import importlib
import os

PredictionResult = Tuple[Optional[str], List[str], Optional[float]]

@lru_cache(maxsize=1)
def get_predictor() -> Callable[..., PredictionResult]:
    module_name = os.getenv(
        "TEMPLATE_PREDICTOR_MODULE",
        "app.ml_predictor",
    )
    module = importlib.import_module(module_name)
    predictor = getattr(module, "predict_template_id", None)
    if not callable(predictor):
        raise RuntimeError(
            "The configured predictor module must define predict_template_id."
        )
    return predictor

def predict_template_id(
    activity_name: str,
    well_name: str,
    service_provider: str,
) -> PredictionResult:
    return get_predictor()(
        activity_name=activity_name,
        well_name=well_name,
        service_provider=service_provider,
    )
