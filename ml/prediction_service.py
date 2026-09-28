"""Assemble one live prediction instance for the application.

The Random Forest, SHAP report, Gemini layer, and recommendation filter must
all describe the same Phase 3 sample. This module never lets Gemini or the
recommendation selector change the predicted category or probability.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib

from .explainability import load_explanation_inputs
from .generative_explanation import _deterministic_fallback, explain_with_gemini
from .model_training import DEFAULT_ARTIFACT_DIR, DEFAULT_DATA
from .recommendation import normalize_category
from .utils import (
    category_display_name,
    customer_gemini_fallback,
    sanitize_customer_text,
    shap_to_friendly_contributors,
    technical_shap_contributors,
)

REPORT_DIR = Path(__file__).parent / "reports"
PHASE4_REPORT = REPORT_DIR / "phase4_shap_validation.json"
LIVE_CACHE = REPORT_DIR / "live_session_explanation.json"
PIPELINE_PATH = DEFAULT_ARTIFACT_DIR / "phase3_random_forest_pipeline.joblib"

_CACHE: dict[str, Any] | None = None


def _json_safe(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _load_phase4_evidence() -> dict[str, Any]:
    if not PHASE4_REPORT.is_file():
        raise FileNotFoundError("Phase 4 SHAP validation report is missing.")
    return json.loads(PHASE4_REPORT.read_text(encoding="utf-8"))


def _verify_saved_prediction(evidence: dict[str, Any]) -> dict[str, Any]:
    """Re-run the locked pipeline on the Phase 4 sample; do not invent values."""
    if not PIPELINE_PATH.is_file():
        return evidence
    row_index = int(evidence.get("source_row_index", 0))
    data_path = Path(evidence.get("data_path") or DEFAULT_DATA)
    if not data_path.is_file():
        data_path = DEFAULT_DATA
    pipeline = joblib.load(PIPELINE_PATH)
    features, _audit = load_explanation_inputs(data_path, row_index)
    predicted = str(pipeline.predict(features)[0])
    probabilities = pipeline.predict_proba(features)[0]
    labels = [str(label) for label in pipeline.named_steps["model"].classes_]
    class_index = labels.index(predicted)
    live_probability = float(probabilities[class_index])
    reported_category = str(evidence.get("predicted_category"))
    if predicted != reported_category:
        raise RuntimeError(
            "Saved SHAP evidence does not match the locked Random Forest prediction "
            f"for row {row_index}: model={predicted}, shap={reported_category}."
        )
    reported_probability = float(evidence.get("prediction_probability"))
    if abs(live_probability - reported_probability) > 1e-6:
        raise RuntimeError(
            "Saved SHAP probability does not match the locked Random Forest probability "
            f"for row {row_index}."
        )
    evidence = dict(evidence)
    evidence["predicted_category"] = predicted
    evidence["prediction_probability"] = reported_probability
    evidence["class_probabilities"] = {
        label: float(probability) for label, probability in zip(labels, probabilities)
    }
    return evidence


def _customer_gemini(evidence: dict[str, Any], contributors: list[dict[str, Any]]) -> dict[str, Any]:
    """Ask Gemini to explain the real evidence using customer-facing labels."""
    predicted = evidence["predicted_category"]
    display = category_display_name(predicted)
    customer_evidence = {
        "predicted_category": display,
        "prediction_probability": evidence["prediction_probability"],
        "top_positive_contributors": [
            {
                "feature": item["feature"],
                "shap_value": item["weight"],
            }
            for item in contributors
            if item["direction"] == "positive"
        ],
        "top_negative_contributors": [
            {
                "feature": item["feature"],
                "shap_value": item["weight"],
            }
            for item in contributors
            if item["direction"] == "negative"
        ],
    }
    result = explain_with_gemini(customer_evidence)
    text = sanitize_customer_text(result.get("explanation", ""), predicted, contributors)
    result["explanation"] = text
    result["model_prediction"] = {
        "predicted_category": predicted,
        "prediction_probability": evidence["prediction_probability"],
        "top_positive_contributors": evidence.get("top_positive_contributors", []),
        "top_negative_contributors": evidence.get("top_negative_contributors", []),
    }
    return result


def assemble_public_explanation(evidence: dict[str, Any], gemini_result: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the unified public explanation payload from one SHAP instance."""
    predicted = str(evidence["predicted_category"])
    canonical = normalize_category(predicted) or predicted
    probability = float(evidence["prediction_probability"])
    contributors = shap_to_friendly_contributors(evidence, limit=4)
    if gemini_result is None:
        gemini_text = customer_gemini_fallback(canonical, contributors)
        gemini_status = "fallback"
        gemini_model = None
    else:
        gemini_text = sanitize_customer_text(gemini_result.get("explanation", ""), canonical, contributors)
        gemini_status = gemini_result.get("status", "unavailable")
        gemini_model = gemini_result.get("model")
    payload = {
        "status": "success",
        "model": "RandomForestClassifier",
        "predicted_category": category_display_name(canonical),
        "predicted_category_canonical": canonical,
        "shap_explained_category": canonical,
        "gemini_explained_category": canonical,
        "recommendation_category": canonical,
        "prediction_probability": probability,
        "shap_contributors": [
            {
                "feature": item["feature"],
                "direction": item["direction"],
                "weight": item["weight"],
            }
            for item in contributors
        ],
        "gemini_explanation": gemini_text,
        "gemini_status": gemini_status,
        "gemini_model": gemini_model,
        "technical_details": {
            "predicted_category": canonical,
            "prediction_probability": probability,
            "class_probabilities": evidence.get("class_probabilities", {}),
            "shap_contributors": technical_shap_contributors(evidence),
            "shap_probability_validation": evidence.get("shap_probability_validation", {}),
            "source_row_index": evidence.get("source_row_index"),
        },
    }
    if not (
        payload["predicted_category_canonical"]
        == payload["shap_explained_category"]
        == payload["gemini_explained_category"]
        == payload["recommendation_category"]
    ):
        raise RuntimeError("Unified explanation categories are inconsistent.")
    return payload


def build_live_explanation(*, verify_pipeline: bool = True) -> dict[str, Any]:
    """Create the application explanation from the same Phase 4 prediction instance."""
    evidence = _load_phase4_evidence()
    if verify_pipeline:
        try:
            evidence = _verify_saved_prediction(evidence)
        except Exception:
            # Keep the saved SHAP instance if the optional live reload is unavailable.
            evidence = _load_phase4_evidence()
    contributors = shap_to_friendly_contributors(evidence, limit=4)
    try:
        gemini_result = _customer_gemini(evidence, contributors)
    except Exception:
        gemini_result = {
            "status": "unavailable",
            "explanation": _deterministic_fallback(
                {
                    "predicted_category": category_display_name(evidence["predicted_category"]),
                    "prediction_probability": evidence["prediction_probability"],
                    "top_positive_contributors": evidence.get("top_positive_contributors", []),
                    "top_negative_contributors": evidence.get("top_negative_contributors", []),
                }
            ),
        }
    payload = assemble_public_explanation(evidence, gemini_result)
    LIVE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    LIVE_CACHE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def get_unified_explanation(*, refresh: bool = False) -> dict[str, Any]:
    """Return the cached unified explanation, building it once if needed."""
    global _CACHE
    if refresh:
        _CACHE = None
    if _CACHE is not None:
        return _CACHE
    if LIVE_CACHE.is_file() and not refresh:
        _CACHE = json.loads(LIVE_CACHE.read_text(encoding="utf-8"))
        return _CACHE
    _CACHE = build_live_explanation()
    return _CACHE
