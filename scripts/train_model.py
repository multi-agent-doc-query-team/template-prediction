"""Train, evaluate, and persist the template-classification model.

The dataset is split by normalized activity text so that the same activity
variant cannot cross train, validation, and test boundaries. Metrics are
reported with a model trained only on the training split. After evaluation, a
deployable model is fitted on train + validation; the test split remains
untouched.

Run from the project root:

    python scripts/train_model.py

Optional paths:

    python scripts/train_model.py \
        --dataset data/trained_dataset.csv \
        --templates data/templates.json \
        --models-dir models
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import joblib
import pandas as pd
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupShuffleSplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.normalization import build_model_text


REQUIRED_COLUMNS = frozenset(
    {
        "service_provider",
        "activity",
        "well_name",
        "template_id",
    }
)
ACTIVITY_GROUP_COLUMN = "activity_group"
VALIDATION_AND_TEST_SIZE = 0.30
TEST_SHARE_OF_HOLDOUT = 0.50
FIRST_SPLIT_RANDOM_STATE = 42
SECOND_SPLIT_RANDOM_STATE = 43
VECTORIZER_PARAMETERS = {
    "analyzer": "char",
    "ngram_range": (3, 5),
    "sublinear_tf": True,
}
MODEL_PARAMETERS = {
    "max_iter": 3000,
    "C": 4.0,
}


@dataclass(frozen=True)
class DatasetSplits:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame


def normalize_activity_group(value: object) -> str:
    """Normalize whitespace and case solely for leakage-safe grouping."""

    return re.sub(r"\s+", " ", str(value).lower()).strip()


def activity_words(value: object) -> set[str]:
    """Return activity tokens used by the familiarity diagnostics."""

    return set(re.findall(r"[a-z0-9]+", str(value).lower()))


def build_feature_texts(frame: pd.DataFrame) -> list[str]:
    """Create model input using the same transformation as the API."""

    return [
        build_model_text(
            activity_name=activity,
            well_name=well,
            service_provider=provider,
        )
        for provider, activity, well in zip(
            frame["service_provider"],
            frame["activity"],
            frame["well_name"],
        )
    ]


def load_dataset(dataset_file: Path) -> pd.DataFrame:
    if not dataset_file.exists():
        raise FileNotFoundError(f"Dataset file does not exist: {dataset_file}")

    data = pd.read_csv(dataset_file).fillna("")
    missing_columns = REQUIRED_COLUMNS.difference(data.columns)

    if missing_columns:
        raise ValueError(
            f"Dataset is missing required columns: {sorted(missing_columns)}"
        )

    if data.empty:
        raise ValueError("Dataset contains no rows.")

    for column in REQUIRED_COLUMNS:
        blank_rows = data[column].astype(str).str.strip().eq("")
        if blank_rows.any():
            row_numbers = (data.index[blank_rows][:5] + 2).tolist()
            raise ValueError(
                f"Dataset column {column!r} contains blank values at CSV rows "
                f"{row_numbers}."
            )

    return data


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


def validate_template_labels(data: pd.DataFrame, template_ids: set[str]) -> None:
    dataset_labels = set(data["template_id"].astype(str))
    unknown_labels = sorted(dataset_labels.difference(template_ids))

    if unknown_labels:
        raise ValueError(
            "Dataset contains template IDs missing from the template file: "
            f"{unknown_labels}"
        )


def split_dataset(data: pd.DataFrame) -> DatasetSplits:
    """Create deterministic splits with disjoint normalized activity groups."""

    prepared = data.copy()
    prepared[ACTIVITY_GROUP_COLUMN] = prepared["activity"].map(
        normalize_activity_group
    )

    first_split = GroupShuffleSplit(
        n_splits=1,
        test_size=VALIDATION_AND_TEST_SIZE,
        random_state=FIRST_SPLIT_RANDOM_STATE,
    )
    train_indices, holdout_indices = next(
        first_split.split(
            prepared,
            groups=prepared[ACTIVITY_GROUP_COLUMN],
        )
    )

    train = prepared.iloc[train_indices].copy()
    holdout = prepared.iloc[holdout_indices].copy()

    second_split = GroupShuffleSplit(
        n_splits=1,
        test_size=TEST_SHARE_OF_HOLDOUT,
        random_state=SECOND_SPLIT_RANDOM_STATE,
    )
    validation_indices, test_indices = next(
        second_split.split(
            holdout,
            groups=holdout[ACTIVITY_GROUP_COLUMN],
        )
    )

    validation = holdout.iloc[validation_indices].copy()
    test = holdout.iloc[test_indices].copy()
    splits = DatasetSplits(train=train, validation=validation, test=test)

    validate_splits(splits)
    return splits


def validate_splits(splits: DatasetSplits) -> None:
    frames = {
        "train": splits.train,
        "validation": splits.validation,
        "test": splits.test,
    }

    for name, frame in frames.items():
        if frame.empty:
            raise ValueError(f"Dataset split is empty: {name}")

    group_sets = {
        name: set(frame[ACTIVITY_GROUP_COLUMN])
        for name, frame in frames.items()
    }
    overlaps = {
        "train_validation": group_sets["train"] & group_sets["validation"],
        "train_test": group_sets["train"] & group_sets["test"],
        "validation_test": group_sets["validation"] & group_sets["test"],
    }

    if any(overlaps.values()):
        overlap_counts = {
            name: len(values) for name, values in overlaps.items()
        }
        raise RuntimeError(
            "Activity groups overlap across dataset splits: "
            f"{overlap_counts}"
        )

    training_labels = set(splits.train["template_id"])
    missing_training_labels = sorted(
        (set(splits.validation["template_id"]) | set(splits.test["template_id"]))
        - training_labels
    )
    if missing_training_labels:
        raise ValueError(
            "Validation or test contains labels absent from training: "
            f"{missing_training_labels}"
        )


def create_vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(**VECTORIZER_PARAMETERS)


def create_model() -> LogisticRegression:
    return LogisticRegression(**MODEL_PARAMETERS)


def train_model(
    frame: pd.DataFrame,
) -> tuple[TfidfVectorizer, LogisticRegression]:
    vectorizer = create_vectorizer()
    features = vectorizer.fit_transform(build_feature_texts(frame))
    model = create_model()
    model.fit(features, frame["template_id"])
    return vectorizer, model


def score_predictions(
    actual: Iterable[str],
    predicted: Iterable[str],
) -> dict[str, float | int]:
    actual_values = list(actual)
    predicted_values = list(predicted)
    return {
        "rows": len(actual_values),
        "accuracy": float(accuracy_score(actual_values, predicted_values)),
        "macro_f1": float(
            f1_score(
                actual_values,
                predicted_values,
                average="macro",
                zero_division=0,
            )
        ),
    }


def familiarity_report(
    frame: pd.DataFrame,
    predicted,
    training_vocabulary: set[str],
) -> dict[str, dict[str, float | int | None]]:
    statuses = [
        "contains_unfamiliar_words"
        if activity_words(activity).difference(training_vocabulary)
        else "all_words_familiar"
        for activity in frame["activity"]
    ]

    report: dict[str, dict[str, float | int | None]] = {}
    for status in ("all_words_familiar", "contains_unfamiliar_words"):
        indices = [
            index
            for index, row_status in enumerate(statuses)
            if row_status == status
        ]

        if not indices:
            report[status] = {
                "rows": 0,
                "accuracy": None,
                "macro_f1": None,
            }
            continue

        report[status] = score_predictions(
            frame["template_id"].to_numpy()[indices],
            predicted[indices],
        )

    return report


def evaluate(
    model: LogisticRegression,
    vectorizer: TfidfVectorizer,
    frame: pd.DataFrame,
    training_vocabulary: set[str] | None = None,
) -> dict:
    features = vectorizer.transform(build_feature_texts(frame))
    predicted = model.predict(features)
    probabilities = model.predict_proba(features)

    result = score_predictions(frame["template_id"], predicted)
    confidence = probabilities.max(axis=1)
    result.update(
        {
            "mean_confidence": float(confidence.mean()),
            "predictions_below_0_60": int((confidence < 0.60).sum()),
        }
    )

    if training_vocabulary is not None:
        result["activity_familiarity"] = familiarity_report(
            frame,
            predicted,
            training_vocabulary,
        )

    return result


def build_training_vocabulary(frame: pd.DataFrame) -> set[str]:
    vocabulary: set[str] = set()
    for activity in frame["activity"]:
        vocabulary.update(activity_words(activity))
    return vocabulary


def build_split_metadata(splits: DatasetSplits) -> dict:
    frames = {
        "train": splits.train,
        "validation": splits.validation,
        "test": splits.test,
    }
    group_sets = {
        name: set(frame[ACTIVITY_GROUP_COLUMN])
        for name, frame in frames.items()
    }
    return {
        "rows": {name: len(frame) for name, frame in frames.items()},
        "activity_groups": {
            name: len(groups) for name, groups in group_sets.items()
        },
        "activity_group_overlap": {
            "train_validation": len(
                group_sets["train"] & group_sets["validation"]
            ),
            "train_test": len(group_sets["train"] & group_sets["test"]),
            "validation_test": len(
                group_sets["validation"] & group_sets["test"]
            ),
        },
    }


def write_artifacts(
    models_dir: Path,
    vectorizer: TfidfVectorizer,
    model: LogisticRegression,
    metadata: dict,
) -> dict[str, str]:
    models_dir.mkdir(parents=True, exist_ok=True)
    vectorizer_file = models_dir / "vectorizer.joblib"
    model_file = models_dir / "template_model.joblib"
    metadata_file = models_dir / "model_metadata.json"

    joblib.dump(vectorizer, vectorizer_file)
    joblib.dump(model, model_file)
    metadata_file.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    return {
        "vectorizer": str(vectorizer_file),
        "model": str(model_file),
        "metadata": str(metadata_file),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "data" / "trained_dataset.csv",
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

    data = load_dataset(dataset_file)
    validate_template_labels(data, load_template_ids(template_file))
    splits = split_dataset(data)
    training_vocabulary = build_training_vocabulary(splits.train)

    evaluation_vectorizer, evaluation_model = train_model(splits.train)
    evaluation = {
        "train": evaluate(
            evaluation_model,
            evaluation_vectorizer,
            splits.train,
        ),
        "validation": evaluate(
            evaluation_model,
            evaluation_vectorizer,
            splits.validation,
            training_vocabulary,
        ),
        "test": evaluate(
            evaluation_model,
            evaluation_vectorizer,
            splits.test,
            training_vocabulary,
        ),
    }

    # Refit the deployable artifacts on train + validation only. The test set
    # remains untouched and is evaluated once more against the final model.
    combined = pd.concat(
        [splits.train, splits.validation],
        ignore_index=True,
    )
    final_vectorizer, final_model = train_model(combined)
    final_test_evaluation = evaluate(
        final_model,
        final_vectorizer,
        splits.test,
        training_vocabulary,
    )

    metadata = {
        "model_version": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "algorithm": "character TF-IDF + logistic regression",
        "scikit_learn_version": sklearn.__version__,
        "dataset_file": str(dataset_file),
        "template_file": str(template_file),
        "total_rows": len(data),
        "class_count": int(data["template_id"].nunique()),
        "split_strategy": {
            "group": "normalized activity text",
            "validation_and_test_size": VALIDATION_AND_TEST_SIZE,
            "test_share_of_holdout": TEST_SHARE_OF_HOLDOUT,
            "random_states": [
                FIRST_SPLIT_RANDOM_STATE,
                SECOND_SPLIT_RANDOM_STATE,
            ],
        },
        "splits": build_split_metadata(splits),
        "vectorizer_parameters": VECTORIZER_PARAMETERS,
        "model_parameters": MODEL_PARAMETERS,
        "evaluation_before_final_refit": evaluation,
        "final_fit_rows": len(combined),
        "final_model_test_evaluation": final_test_evaluation,
    }
    artifacts = write_artifacts(
        models_dir,
        final_vectorizer,
        final_model,
        metadata,
    )

    print(
        json.dumps(
            {
                "evaluation": evaluation,
                "final_model_test_evaluation": final_test_evaluation,
                "artifacts": artifacts,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        print(f"Training failed: {error}", file=sys.stderr)
        raise SystemExit(1)
