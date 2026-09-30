"""Train and evaluate the template-classification model.

Run from the project root:

    python scripts/train_model.py \
        --dataset data/dataset.csv \
        --templates data/templates.json

The script trains only on rows whose split is ``train``. Validation and test
rows are used only for evaluation. It writes the model artifacts to ``models``.
"""

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.normalization import normalize_activity_name, normalize_provider_name
from app.services.tools.predictor import normalize_value


REQUIRED_COLUMNS = {
    "service_provider",
    "activity",
    "well_name",
    "template_id",
    "split",
}


def build_model_text(row: Dict[str, str]) -> str:
    """Build the same normalized feature text used by the API predictor."""

    provider = normalize_provider_name(row["service_provider"])
    activity = normalize_activity_name(row["activity"])
    well = normalize_value(row["well_name"])

    return f"provider={provider} activity={activity} well={well}"


def load_rows(dataset_file: Path) -> List[Dict[str, str]]:
    if not dataset_file.exists():
        raise FileNotFoundError(f"Dataset file does not exist: {dataset_file}")

    with dataset_file.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            missing = REQUIRED_COLUMNS.difference(reader.fieldnames or set())
            raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")

        rows = []
        for row in reader:
            if any(not row.get(column, "").strip() for column in REQUIRED_COLUMNS):
                raise ValueError(f"Dataset contains an incomplete row: {row}")
            rows.append(row)

    if not rows:
        raise ValueError("Dataset contains no rows.")

    return rows


def load_template_ids(template_file: Path) -> set[str]:
    if not template_file.exists():
        raise FileNotFoundError(f"Template file does not exist: {template_file}")

    with template_file.open("r", encoding="utf-8") as file:
        templates = json.load(file)

    if not isinstance(templates, list):
        raise ValueError("Template file must contain a JSON list.")

    template_ids = {
        template.get("template_id")
        for template in templates
        if isinstance(template, dict) and template.get("template_id")
    }

    if not template_ids:
        raise ValueError("Template file contains no template IDs.")

    return template_ids


def split_rows(rows: Iterable[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    split_data: Dict[str, List[Dict[str, str]]] = {
        "train": [],
        "val": [],
        "test": [],
    }

    for row in rows:
        split = row["split"].strip().lower()
        if split not in split_data:
            raise ValueError(f"Unsupported split value: {row['split']}")
        split_data[split].append(row)

    for split, split_rows_value in split_data.items():
        if not split_rows_value:
            raise ValueError(f"Dataset split is empty: {split}")

    return split_data


def evaluate(
    model: LogisticRegression,
    features,
    labels: List[str],
) -> Dict:
    predictions = model.predict(features)
    label_order = sorted(set(labels).union(predictions))

    return {
        "rows": len(labels),
        "accuracy": float(accuracy_score(labels, predictions)),
        "macro_f1": float(
            f1_score(labels, predictions, average="macro", zero_division=0)
        ),
        "classification_report": classification_report(
            labels,
            predictions,
            labels=label_order,
            output_dict=True,
            zero_division=0,
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "data" / "dataset.csv",
    )
    parser.add_argument(
        "--templates",
        type=Path,
        default=PROJECT_ROOT / "data" / "templates.json",
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=PROJECT_ROOT / "models",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset_file = args.dataset.resolve()
    template_file = args.templates.resolve()
    models_dir = args.models_dir.resolve()

    rows = load_rows(dataset_file)
    template_ids = load_template_ids(template_file)
    unknown_labels = sorted(
        {row["template_id"] for row in rows}.difference(template_ids)
    )

    if unknown_labels:
        raise ValueError(
            "Dataset contains template IDs missing from the template file: "
            f"{unknown_labels}"
        )

    split_data = split_rows(rows)
    train_rows = split_data["train"]

    train_text = [build_model_text(row) for row in train_rows]
    train_labels = [row["template_id"] for row in train_rows]

    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=1,
    )
    train_features = vectorizer.fit_transform(train_text)

    model = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=42,
    )
    model.fit(train_features, train_labels)

    metrics = {}
    for split_name, split_rows_value in split_data.items():
        texts = [build_model_text(row) for row in split_rows_value]
        labels = [row["template_id"] for row in split_rows_value]
        features = vectorizer.transform(texts)
        metrics[split_name] = evaluate(model, features, labels)

    models_dir.mkdir(parents=True, exist_ok=True)
    vectorizer_file = models_dir / "vectorizer.joblib"
    model_file = models_dir / "template_model.joblib"
    metadata_file = models_dir / "model_metadata.json"

    joblib.dump(vectorizer, vectorizer_file)
    joblib.dump(model, model_file)

    metadata = {
        "model_version": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "algorithm": "TfidfVectorizer + LogisticRegression",
        "dataset_file": str(dataset_file),
        "template_file": str(template_file),
        "total_rows": len(rows),
        "split_counts": {
            split: len(values) for split, values in split_data.items()
        },
        "class_count": len(set(row["template_id"] for row in rows)),
        "class_counts_in_train": dict(Counter(train_labels)),
        "metrics": metrics,
        "artifacts": {
            "vectorizer": str(vectorizer_file),
            "model": str(model_file),
        },
    }
    metadata_file.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print(json.dumps({"metrics": metrics, "metadata": str(metadata_file)}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError) as error:
        print(f"Training failed: {error}", file=sys.stderr)
        raise SystemExit(1)
