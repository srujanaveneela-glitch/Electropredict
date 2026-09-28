"""SHAP explanations for the saved ElectroPredict Phase 3 pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .model_training import (
    CATEGORICAL_HISTORY_COLUMNS,
    DEFAULT_DATA,
    DEFAULT_ARTIFACT_DIR,
    FORBIDDEN_FEATURE_COLUMNS,
    FrequencyCapper,
    TARGET_COLUMN,
)

DEFAULT_REPORT = Path(__file__).parent / "reports" / "phase4_shap_validation.json"


def _json_value(value: Any) -> Any:
    """Convert numpy/pandas scalars to JSON-safe values without exposing IDs."""
    if pd.isna(value):
        return None
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    return value


def load_explanation_inputs(data_path: Path, row_index: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load one Phase 2 row and keep audit data separate from model inputs."""
    data = pd.read_csv(data_path, compression="infer")
    if TARGET_COLUMN not in data or "prediction_timestamp" not in data:
        raise ValueError("Phase 2 data is missing the target or prediction timestamp.")
    data["prediction_timestamp"] = pd.to_datetime(data["prediction_timestamp"], utc=True, errors="coerce")
    data = data.sort_values("prediction_timestamp", kind="mergesort").reset_index(drop=True)
    if row_index < 0 or row_index >= len(data):
        raise IndexError(f"row_index must be between 0 and {len(data) - 1}")
    feature_columns = [column for column in data.columns if column not in FORBIDDEN_FEATURE_COLUMNS]
    features = data.loc[[row_index], feature_columns].copy()
    for column in CATEGORICAL_HISTORY_COLUMNS:
        if column not in features:
            raise ValueError(f"Missing categorical history feature: {column}")
        features[column] = features[column].astype("string")
    return features, data.loc[[row_index]]


def load_training_background(data_path: Path, max_rows: int = 100) -> pd.DataFrame:
    """Load a deterministic background sample from the Phase 3 training period."""
    data = pd.read_csv(data_path, compression="infer")
    if TARGET_COLUMN not in data or "prediction_timestamp" not in data:
        raise ValueError("Phase 2 data is missing the target or prediction timestamp.")
    data["prediction_timestamp"] = pd.to_datetime(data["prediction_timestamp"], utc=True, errors="coerce")
    data = data.sort_values("prediction_timestamp", kind="mergesort").reset_index(drop=True)
    if len(data) < 2:
        raise ValueError("Phase 2 data must contain at least two rows for a chronological split.")
    split_index = max(1, min(len(data) - 1, int(len(data) * 0.8)))
    feature_columns = [column for column in data.columns if column not in FORBIDDEN_FEATURE_COLUMNS]
    background = data.iloc[:split_index].loc[:, feature_columns].head(max_rows).copy()
    for column in CATEGORICAL_HISTORY_COLUMNS:
        if column not in background:
            raise ValueError(f"Missing categorical history feature: {column}")
        background[column] = background[column].astype("string")
    if background.empty:
        raise ValueError("The Phase 3 training portion produced an empty SHAP background.")
    return background


def _transformed_feature_sources(preprocessor) -> tuple[np.ndarray, list[str]]:
    """Map each transformed feature to its original source feature."""
    names = np.asarray(preprocessor.get_feature_names_out(), dtype=object)
    sources: list[str] = []
    for transformer_name, transformer, columns in preprocessor.transformers_:
        if transformer_name == "remainder" or transformer == "drop":
            continue
        column_names = list(columns)
        transformed_names = list(transformer.get_feature_names_out(column_names))
        for transformed_name in transformed_names:
            matching_columns = [
                column
                for column in column_names
                if transformed_name == column or transformed_name.startswith(f"{column}_")
            ]
            if not matching_columns:
                raise ValueError(
                    f"Could not identify source feature for transformed feature {transformed_name!r} "
                    f"from transformer {transformer_name!r}."
                )
            sources.append(max(matching_columns, key=len))
    if len(sources) != len(names):
        raise ValueError(
            f"Could not map transformed features to source features: {len(names)} names, {len(sources)} sources."
        )
    return names, sources


def _class_shap_values(shap_values: Any, class_index: int, feature_count: int) -> np.ndarray:
    """Normalize SHAP's old list and new multiclass ndarray formats."""
    if isinstance(shap_values, list):
        return np.asarray(shap_values[class_index])[0]
    values = np.asarray(shap_values)
    if values.ndim != 3:
        raise ValueError(f"Unexpected multiclass SHAP shape: {values.shape}")
    if values.shape[1] == feature_count:
        return values[0, :, class_index]
    if values.shape[2] == feature_count:
        return values[0, class_index, :]
    raise ValueError(f"Could not identify feature axis in SHAP shape: {values.shape}")


def explain_prediction(
    pipeline,
    features: pd.DataFrame,
    background_features: pd.DataFrame,
    *,
    top_n: int = 10,
) -> dict:
    """Return actual prediction probabilities and class-specific TreeSHAP values."""
    try:
        import shap
    except ImportError as exc:
        raise RuntimeError("SHAP is required for Phase 4. Install it in the Conda environment.") from exc

    preprocessor = pipeline.named_steps["preprocessing"]
    model = pipeline.named_steps["model"]
    transformed = preprocessor.transform(features)
    transformed_background = preprocessor.transform(background_features)
    transformed_for_shap = transformed.toarray() if hasattr(transformed, "toarray") else transformed
    background_matrix = (
        transformed_background.toarray()
        if hasattr(transformed_background, "toarray")
        else transformed_background
    )
    transformed_for_shap = np.asarray(transformed_for_shap, dtype=np.float64)
    background_matrix = np.asarray(background_matrix, dtype=np.float64)
    if transformed_for_shap.ndim != 2:
        raise ValueError(f"Expected a 2-D transformed matrix, got shape {transformed_for_shap.shape}.")
    if background_matrix.ndim != 2:
        raise ValueError(f"Expected a 2-D background matrix, got shape {background_matrix.shape}.")
    if transformed_for_shap.shape[1] != 1209 or background_matrix.shape[1] != 1209:
        raise ValueError(
            "Phase 4 expects exactly 1209 transformed features: "
            f"explained row has {transformed_for_shap.shape[1]}, background has {background_matrix.shape[1]}."
        )
    if transformed_for_shap.shape[1] != model.n_features_in_:
        raise ValueError(
            "The transformed matrix does not match the fitted RandomForestClassifier: "
            f"matrix has {transformed_for_shap.shape[1]} features, model expects {model.n_features_in_}."
        )
    if not np.isfinite(transformed_for_shap).all() or not np.isfinite(background_matrix).all():
        raise ValueError("The transformed SHAP matrices contain non-finite values.")
    transformed_names, source_names = _transformed_feature_sources(preprocessor)
    prediction = model.predict(transformed_for_shap)[0]
    probabilities = model.predict_proba(transformed_for_shap)[0]
    class_labels = [str(label) for label in model.classes_]
    class_index = class_labels.index(str(prediction))

    explainer = shap.TreeExplainer(
        model,
        data=background_matrix,
        feature_perturbation="interventional",
        model_output="probability",
    )
    shap_explanation = explainer(transformed_for_shap, check_additivity=True)
    shap_values = shap_explanation.values
    class_values = _class_shap_values(shap_values, class_index, transformed_for_shap.shape[1])
    expected_values = np.asarray(explainer.expected_value, dtype=np.float64).reshape(-1)
    if class_index >= len(expected_values):
        raise ValueError(
            f"SHAP expected_value has {len(expected_values)} outputs, missing class index {class_index}."
        )
    expected_probability = float(expected_values[class_index])
    model_probability = float(probabilities[class_index])
    shap_reconstructed_probability = expected_probability + float(class_values.sum())
    shap_probability_absolute_difference = abs(shap_reconstructed_probability - model_probability)
    source_values = features.iloc[0].to_dict()
    contributions = []
    for transformed_name, source_name, value in zip(transformed_names, source_names, class_values):
        contributions.append(
            {
                "feature": source_name,
                "transformed_feature": str(transformed_name),
                "feature_value": _json_value(source_values.get(source_name)),
                "shap_value": float(value),
            }
        )
    contributions.sort(key=lambda item: abs(item["shap_value"]), reverse=True)
    positive = [item for item in contributions if item["shap_value"] > 0][:top_n]
    negative = [item for item in contributions if item["shap_value"] < 0][:top_n]
    return {
        "model": "RandomForestClassifier",
        "target": TARGET_COLUMN,
        "predicted_category": str(prediction),
        "prediction_probability": float(probabilities[class_index]),
        "shap_probability_validation": {
            "expected_value": expected_probability,
            "shap_sum_for_predicted_class": float(class_values.sum()),
            "reconstructed_probability": shap_reconstructed_probability,
            "model_probability": model_probability,
            "absolute_difference": shap_probability_absolute_difference,
        },
        "class_probabilities": {
            label: float(probability) for label, probability in zip(class_labels, probabilities)
        },
        "shap_output_structure": {
            "raw_type": type(shap_values).__name__,
            "raw_shape": [list(np.asarray(value).shape) for value in shap_values]
            if isinstance(shap_values, list)
            else list(np.asarray(shap_values).shape),
            "explained_class": str(prediction),
            "explained_class_index": class_index,
            "transformed_feature_count": int(transformed_for_shap.shape[1]),
            "background_row_count": int(background_matrix.shape[0]),
            "background_feature_count": int(background_matrix.shape[1]),
        },
        "top_positive_contributors": positive,
        "top_negative_contributors": negative,
        "all_class_specific_contributions": contributions,
    }


def run_shap_validation(
    data_path: Path = DEFAULT_DATA,
    pipeline_path: Path = DEFAULT_ARTIFACT_DIR / "phase3_random_forest_pipeline.joblib",
    report_path: Path = DEFAULT_REPORT,
    row_index: int = 0,
    top_n: int = 10,
) -> dict:
    """Load the locked pipeline, explain one real Phase 2 sample, and save a report."""
    pipeline = joblib.load(pipeline_path)
    features, _audit_row = load_explanation_inputs(data_path, row_index)
    background_features = load_training_background(data_path)
    explanation = explain_prediction(pipeline, features, background_features, top_n=top_n)
    report = {
        "phase": 4,
        "pipeline_path": str(pipeline_path),
        "data_path": str(data_path),
        "explained_samples": 1,
        "source_row_index": row_index,
        "audit_identifiers_included": False,
        "prediction_matches_explained_class": True,
        **explanation,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--pipeline", type=Path, default=DEFAULT_ARTIFACT_DIR / "phase3_random_forest_pipeline.joblib")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--row-index", type=int, default=0)
    parser.add_argument("--top-n", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(run_shap_validation(args.data, args.pipeline, args.report, args.row_index, args.top_n), indent=2))


if __name__ == "__main__":
    main()
