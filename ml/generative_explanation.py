"""Evidence-constrained Gemini explanations for Phase 4 model outputs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

DEFAULT_MODEL = "gemini-3.6-flash"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
DEFAULT_SHAP_REPORT = Path(__file__).parent / "reports" / "phase4_shap_validation.json"
DEFAULT_REPORT = Path(__file__).parent / "reports" / "phase5_gemini_validation.json"
API_KEY_ENVIRONMENT_VARIABLE = "GEMINI_API_KEY"
MAX_CONTRIBUTIONS = 10
FORBIDDEN_EVIDENCE_NAMES = {
    "user_id",
    "order_id",
    "target_order_id",
    "history_end_order_id",
    "history_end_timestamp",
    "prediction_timestamp",
}


def _safe_feature_name(feature: Any) -> bool:
    """Reject identity and audit fields before evidence reaches Gemini."""
    name = str(feature)
    lowered = name.lower()
    return name not in FORBIDDEN_EVIDENCE_NAMES and not any(
        token in lowered for token in ("user_id", "order_id", "timestamp", "target_order")
    )


def _aggregate_contributors(contributors: Any, limit: int | None = None) -> list[dict[str, Any]]:
    """Aggregate transformed SHAP entries by their Phase 4 source feature."""
    aggregated: dict[str, dict[str, Any]] = {}
    if not isinstance(contributors, list):
        return []
    for item in contributors:
        if not isinstance(item, dict):
            continue
        feature = item.get("feature")
        if feature is None or not _safe_feature_name(feature):
            continue
        try:
            shap_value = float(item["shap_value"])
        except (KeyError, TypeError, ValueError):
            continue
        entry = aggregated.setdefault(
            str(feature),
            {
                "feature": str(feature),
                "feature_value": item.get("feature_value"),
                "shap_value": 0.0,
            },
        )
        entry["shap_value"] += shap_value
    result = list(aggregated.values())
    result.sort(key=lambda item: abs(float(item["shap_value"])), reverse=True)
    return result if limit is None else result[:limit]


def _deterministic_fallback(evidence: dict[str, Any]) -> str:
    """Explain the supplied evidence without adding model conclusions."""
    payload = _evidence_payload(evidence)
    category = payload["predicted_category"]
    probability = payload["prediction_probability"]
    positive = payload["top_positive_contributors"][:3]
    negative = payload["top_negative_contributors"][:3]
    positive_text = ", ".join(str(item["feature"]) for item in positive) or "no positive SHAP contributors were available"
    negative_text = ", ".join(str(item["feature"]) for item in negative) or "no negative SHAP contributors were available"
    return (
        f"The model predicted {category} with probability {probability}. "
        f"The main factors contributing toward this prediction were {positive_text}. "
        f"Factors contributing less strongly or away from the prediction included {negative_text}. "
        "These are model associations, not guaranteed purchase outcomes."
    )


def _evidence_payload(evidence: dict[str, Any]) -> dict[str, Any]:
    """Allow only prediction, safe feature evidence, and actual SHAP contributors."""
    required = {"predicted_category", "prediction_probability"}
    missing = required.difference(evidence)
    if missing:
        raise ValueError(f"Missing required model evidence: {sorted(missing)}")
    positive = _aggregate_contributors(
        evidence.get("all_class_specific_contributions", evidence.get("top_positive_contributors", []))
    )
    negative = _aggregate_contributors(
        evidence.get("all_class_specific_contributions", evidence.get("top_negative_contributors", []))
    )
    if evidence.get("all_class_specific_contributions"):
        positive = [item for item in positive if float(item["shap_value"]) > 0][:MAX_CONTRIBUTIONS]
        negative = [item for item in negative if float(item["shap_value"]) < 0][:MAX_CONTRIBUTIONS]
    else:
        positive = [item for item in positive if float(item["shap_value"]) > 0]
        negative = [item for item in negative if float(item["shap_value"]) < 0]
    return {
        "predicted_category": evidence["predicted_category"],
        "prediction_probability": evidence["prediction_probability"],
        "top_positive_contributors": positive,
        "top_negative_contributors": negative,
    }


def build_prompt(evidence: dict[str, Any]) -> str:
    """Build a constrained prompt from actual model/SHAP evidence only."""
    payload = json.dumps(_evidence_payload(evidence), ensure_ascii=True, indent=2)
    return f"""You are explaining an existing machine-learning prediction for an electronics purchase-category model.

The predicted category, probability, feature values, and SHAP contributions in the evidence are authoritative values supplied by the Random Forest and SHAP system. Do not change or recalculate them. Do not invent numerical values, feature values, purchase history, or SHAP values. Use only the supplied evidence. Explain why the model made this prediction in simple language. Clearly distinguish model prediction from explanation. Do not claim causation; describe features as factors that contributed to the model prediction. Do not predict an exact product or purchase date. Do not mention or request user identifiers.

Return a concise plain-text explanation suitable for an application result page. State the predicted category and probability exactly as supplied. Discuss positive SHAP contributors as factors pushing the model toward the predicted category and negative SHAP contributors as factors pushing away from it. End by stating that this is a model association, not a guaranteed purchase.

Evidence from the existing Random Forest and actual TreeSHAP calculation:
{payload}
"""


def explain_with_gemini(
    evidence: dict[str, Any],
    *,
    api_key: str | None = None,
    model_name: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    """Call Gemini only as a language explanation layer, never as the predictor."""
    resolved_key = api_key or os.environ.get(API_KEY_ENVIRONMENT_VARIABLE)
    prompt = build_prompt(evidence)
    if not resolved_key:
        return {
            "status": "unavailable",
            "error": f"Missing {API_KEY_ENVIRONMENT_VARIABLE} environment variable.",
            "prompt_sent": False,
            "explanation": _deterministic_fallback(evidence),
            "model_prediction": _evidence_payload(evidence),
        }

    try:
        from google import genai
    except ImportError as exc:
        return {
            "status": "unavailable",
            "error": "The google-genai package is not installed in the active environment.",
            "prompt_sent": False,
            "explanation": _deterministic_fallback(evidence),
            "model_prediction": _evidence_payload(evidence),
        }

    try:
        client = genai.Client(api_key=resolved_key)
        response = client.models.generate_content(model=model_name, contents=prompt)
        text = getattr(response, "text", None)
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Gemini returned an empty response.")
        return {
            "status": "success",
            "model": model_name,
            "prompt_sent": True,
            "explanation": text.strip(),
            "model_prediction": _evidence_payload(evidence),
        }
    except Exception as exc:  # Network/API errors must not break the prediction path.
        error_detail = str(exc).replace(resolved_key, "[REDACTED]")
        return {
            "status": "unavailable",
            "model": model_name,
            "error": f"Gemini request failed: {type(exc).__name__}: {error_detail}",
            "prompt_sent": True,
            "explanation": _deterministic_fallback(evidence),
            "model_prediction": _evidence_payload(evidence),
        }


def run_gemini_validation(
    shap_report_path: Path = DEFAULT_SHAP_REPORT,
    report_path: Path = DEFAULT_REPORT,
    model_name: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    """Generate a Phase 5 validation report from the actual Phase 4 evidence."""
    shap_report = json.loads(shap_report_path.read_text(encoding="utf-8"))
    result = explain_with_gemini(shap_report, model_name=model_name)
    report = {
        "phase": 5,
        "provider": "Google Gemini",
        "api_key_environment_variable": API_KEY_ENVIRONMENT_VARIABLE,
        "api_key_configured": bool(os.environ.get(API_KEY_ENVIRONMENT_VARIABLE)),
        "prediction_source": "saved Phase 3 RandomForestClassifier",
        "evidence_source": str(shap_report_path),
        "prediction_change_allowed": False,
        "shap_values_change_allowed": False,
        "prompt_contains_anti_fabrication_rules": all(
            phrase in build_prompt(shap_report)
            for phrase in (
                "authoritative values supplied by the Random Forest and SHAP system",
                "Do not change or recalculate them",
                "actual TreeSHAP",
            )
        ),
        "result": result,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shap-report", type=Path, default=DEFAULT_SHAP_REPORT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()
    print(json.dumps(run_gemini_validation(args.shap_report, args.report, args.model), indent=2))


if __name__ == "__main__":
    main()
