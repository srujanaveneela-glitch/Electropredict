"""Train and evaluate the Phase 3 temporal Random Forest classifier.

Run from the project root with::

    python -m ml.model_training

This is the first phase that trains a model. It does not modify the source CSV,
Phase 2 data, Flask application, database, frontend, or any later-phase service.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .model_evaluation import evaluate_classifier, save_classification_report

TARGET_COLUMN = "next_purchase_category"
TIMESTAMP_COLUMN = "prediction_timestamp"
FORBIDDEN_FEATURE_COLUMNS = {
    TARGET_COLUMN,
    "user_id",
    "history_end_order_id",
    "history_end_timestamp",
    "target_order_id",
    TIMESTAMP_COLUMN,
}
DEFAULT_DATA = Path(__file__).parent / "data" / "phase2_training.csv.gz"
DEFAULT_ARTIFACT_DIR = Path(__file__).parent / "artifacts"
DEFAULT_REPORT_DIR = Path(__file__).parent / "reports"
CATEGORICAL_HISTORY_COLUMNS = {
    "previous_product",
    "previous_brand",
    "previous_category",
    "most_frequent_previous_category",
}


class FrequencyCapper(BaseEstimator, TransformerMixin):
    """Replace infrequent categorical values using training data frequencies only."""

    def __init__(self, min_frequency: int = 10):
        self.min_frequency = min_frequency

    def fit(self, x, y=None):
        frame = self._as_frame(x)
        self.feature_names_in_ = np.asarray(frame.columns, dtype=object)
        self.frequent_values_ = {
            column: set(frame[column].value_counts(dropna=False).loc[lambda counts: counts >= self.min_frequency].index)
            for column in frame.columns
        }
        return self

    def transform(self, x):
        frame = self._as_frame(x).copy()
        for column in frame.columns:
            allowed = self.frequent_values_[column]
            frame[column] = frame[column].where(frame[column].isin(allowed), "__rare__")
        return frame

    def get_feature_names_out(self, input_features=None):
        if input_features is None:
            return self.feature_names_in_
        return np.asarray(input_features, dtype=object)

    @staticmethod
    def _as_frame(x):
        if isinstance(x, pd.DataFrame):
            return x
        return pd.DataFrame(x)


def load_phase2_data(data_path: Path) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    """Load Phase 2 data and enforce the feature exclusion contract."""
    data = pd.read_csv(data_path, compression="infer")
    if TARGET_COLUMN not in data.columns or TIMESTAMP_COLUMN not in data.columns:
        raise ValueError(f"Phase 2 data must contain {TARGET_COLUMN!r} and {TIMESTAMP_COLUMN!r}.")

    data[TIMESTAMP_COLUMN] = pd.to_datetime(data[TIMESTAMP_COLUMN], utc=True, errors="coerce")
    if data[TIMESTAMP_COLUMN].isna().any():
        raise ValueError("Phase 2 contains invalid prediction timestamps.")
    data = data.sort_values(TIMESTAMP_COLUMN, kind="mergesort").reset_index(drop=True)
    feature_columns = [column for column in data.columns if column not in FORBIDDEN_FEATURE_COLUMNS]
    if not feature_columns:
        raise ValueError("No model features remain after forbidden-column exclusion.")
    forbidden_in_features = FORBIDDEN_FEATURE_COLUMNS.intersection(feature_columns)
    if forbidden_in_features:
        raise AssertionError(f"Forbidden columns entered features: {sorted(forbidden_in_features)}")
    return data[feature_columns], data[TARGET_COLUMN].astype("string"), feature_columns


def create_pipeline(numeric_columns: list[str], categorical_columns: list[str]) -> Pipeline:
    """Create preprocessing and Random Forest stages."""
    numeric = Pipeline([("imputer", SimpleImputer(strategy="median"))])
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="constant", fill_value="__missing__")),
            ("frequency_capper", FrequencyCapper(min_frequency=10)),
            ("one_hot", OneHotEncoder(handle_unknown="ignore", sparse_output=True)),
        ]
    )
    preprocessing = ColumnTransformer(
        [("numeric", numeric, numeric_columns), ("categorical", categorical, categorical_columns)],
        remainder="drop",
        verbose_feature_names_out=False,
    )
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    return Pipeline([("preprocessing", preprocessing), ("model", model)])


def train_phase3(
    data_path: Path = DEFAULT_DATA,
    artifact_dir: Path = DEFAULT_ARTIFACT_DIR,
    report_dir: Path = DEFAULT_REPORT_DIR,
    train_fraction: float = 0.8,
) -> dict:
    """Fit on the earlier period, evaluate on the later period, and save artifacts."""
    raw = pd.read_csv(data_path, compression="infer")
    if TARGET_COLUMN not in raw or TIMESTAMP_COLUMN not in raw:
        raise ValueError("Phase 2 data is missing the target or prediction timestamp.")
    raw[TIMESTAMP_COLUMN] = pd.to_datetime(raw[TIMESTAMP_COLUMN], utc=True, errors="coerce")
    raw = raw.sort_values(TIMESTAMP_COLUMN, kind="mergesort").reset_index(drop=True)
    feature_columns = [column for column in raw.columns if column not in FORBIDDEN_FEATURE_COLUMNS]
    if set(feature_columns) & FORBIDDEN_FEATURE_COLUMNS:
        raise AssertionError("A forbidden target, identity, audit, or timestamp column is in the feature set.")
    x = raw[feature_columns]
    missing_categorical_columns = CATEGORICAL_HISTORY_COLUMNS.difference(x.columns)
    if missing_categorical_columns:
        raise ValueError(
            f"Phase 2 data is missing required categorical history columns: "
            f"{sorted(missing_categorical_columns)}"
        )
    x = x.copy()
    for column in CATEGORICAL_HISTORY_COLUMNS:
        x[column] = x[column].astype("string")
    y = raw[TARGET_COLUMN].astype("string")
    split_index = max(1, min(len(raw) - 1, int(len(raw) * train_fraction)))
    x_train, x_test = x.iloc[:split_index], x.iloc[split_index:]
    y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]
    split_boundary = raw.loc[split_index, TIMESTAMP_COLUMN]

    numeric_columns = [
        column
        for column in x_train.select_dtypes(include=["number", "bool"]).columns
        if column not in CATEGORICAL_HISTORY_COLUMNS
    ]
    categorical_columns = [
        column for column in feature_columns if column not in numeric_columns
    ]
    pipeline = create_pipeline(numeric_columns, categorical_columns)
    pipeline.fit(x_train, y_train)

    artifact_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    evaluation = evaluate_classifier(pipeline, x_test, y_test, sorted(y.unique()), report_dir)
    save_classification_report(evaluation, report_dir)

    transformed_names = pipeline.named_steps["preprocessing"].get_feature_names_out()
    importances = pipeline.named_steps["model"].feature_importances_
    importance = pd.DataFrame({"feature": transformed_names, "importance": importances})
    importance.sort_values("importance", ascending=False).to_csv(
        report_dir / "feature_importance.csv", index=False
    )

    pipeline_path = artifact_dir / "phase3_random_forest_pipeline.joblib"
    joblib.dump(pipeline, pipeline_path)
    # Loading immediately catches serialization problems before the run is reported successful.
    joblib.load(pipeline_path)

    report = {
        "phase": 3,
        "data_path": str(data_path),
        "pipeline_path": str(pipeline_path),
        "model": "RandomForestClassifier",
        "random_state": 42,
        "target_column": TARGET_COLUMN,
        "feature_column_count": len(feature_columns),
        "feature_columns": feature_columns,
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "explicit_categorical_history_columns": sorted(CATEGORICAL_HISTORY_COLUMNS),
        "forbidden_columns": sorted(FORBIDDEN_FEATURE_COLUMNS),
        "train_samples": int(len(x_train)),
        "test_samples": int(len(x_test)),
        "train_start_timestamp": raw[TIMESTAMP_COLUMN].iloc[0].isoformat(),
        "train_end_timestamp": raw[TIMESTAMP_COLUMN].iloc[split_index - 1].isoformat(),
        "test_start_timestamp": raw[TIMESTAMP_COLUMN].iloc[split_index].isoformat(),
        "test_end_timestamp": raw[TIMESTAMP_COLUMN].iloc[-1].isoformat(),
        "split_boundary_test_start": split_boundary.isoformat(),
        "preprocessing_fit_on_training_only": True,
        "temporal_split_without_shuffle": True,
        "forbidden_columns_excluded": not (set(feature_columns) & FORBIDDEN_FEATURE_COLUMNS),
        "saved_pipeline_reload_check": True,
        "evaluation": evaluation,
    }
    (report_dir / "phase3_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--train-fraction", type=float, default=0.8)
    args = parser.parse_args()
    print(json.dumps(train_phase3(args.data, args.artifact_dir, args.report_dir, args.train_fraction), indent=2))


if __name__ == "__main__":
    main()
