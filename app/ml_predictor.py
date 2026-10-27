from functools import lru_cache
from app.utils.constants import TEMPLATE_MODEL_FILE, VECTORIZER_FILE
from app.utils.normalization import build_model_text
import joblib

@lru_cache(maxsize=1)
def load_model_bundle():
    return (
        joblib.load(VECTORIZER_FILE),
        joblib.load(TEMPLATE_MODEL_FILE),
    )

def predict_template_id(
    activity_name: str,
    well_name: str,
    service_provider: str,
):
    model_text = build_model_text(
        activity_name=activity_name,
        well_name=well_name,
        service_provider=service_provider,
    )
    vectorizer, model = load_model_bundle()
    features = vectorizer.transform([model_text])
    predicted_template_id = model.predict(features)[0]
    confidence = None
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(features)[0]
        confidence = float(max(probabilities))
    elif hasattr(model, "decision_function"):
        import numpy as np
        scores = np.asarray(model.decision_function(features)).reshape(-1)
        if len(scores) == 1:
            confidence = float(1 / (1 + np.exp(-abs(float(scores[0])))))
        else:
            exp_scores = np.exp(scores - np.max(scores))
            confidence = float(np.max(exp_scores / exp_scores.sum()))
    return str(predicted_template_id), [], confidence
