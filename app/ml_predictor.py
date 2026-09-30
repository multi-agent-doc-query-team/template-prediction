from pathlib import Path

import joblib

from app.utils.normalization import build_model_text


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models"

vectorizer = joblib.load(MODEL_DIR / "vectorizer.joblib")
model = joblib.load(MODEL_DIR / "template_model.joblib")


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

    features = vectorizer.transform([model_text])
    predicted_template_id = model.predict(features)[0]

    confidence = None

    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(features)[0]
        confidence = float(max(probabilities))
    elif hasattr(model, "decision_function"):
        # Convert decision scores into a probability-like confidence value.
        import numpy as np

        scores = np.asarray(model.decision_function(features)).reshape(-1)

        if len(scores) == 1:
            confidence = float(1 / (1 + np.exp(-abs(float(scores[0])))))
        else:
            exp_scores = np.exp(scores - np.max(scores))
            confidence = float(np.max(exp_scores / exp_scores.sum()))

    return str(predicted_template_id), [], confidence
