"""Validate that every template in the configured repository is predictable."""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.tools.predictor import load_templates, predict_catalog_template_id


def main() -> int:
    failures = []

    for template in load_templates():
        provider = template.get("provider")
        activity = template.get("activity")
        template_id = template.get("template_id")

        for well_name in template.get("well_names", []):
            predicted_id, errors = predict_catalog_template_id(
                activity_name=activity,
                well_name=well_name,
                service_provider=provider,
            )
            if predicted_id != template_id or errors:
                failures.append(template_id)

    if failures:
        print(f"Prediction validation failed for: {', '.join(failures)}")
        return 1

    print("Prediction validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
