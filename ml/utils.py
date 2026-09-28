"""Customer-facing labels for model categories and SHAP feature names."""

from __future__ import annotations

from typing import Any

from .recommendation import CATALOGUE_CATEGORY_MAP, normalize_category

CATEGORY_DISPLAY_NAMES = {
    "smartphone": "Smartphones",
    "laptop_notebook": "Laptops",
    "tablet": "Tablets",
    "smartwatch_clocks": "Smart Watches",
    "audio": "Headphones",
    "video": "Video",
    "computer_peripherals": "Computer Peripherals",
    "computer_components": "Computer Components",
    "telephone": "Telephones",
    "desktop": "Desktops",
    "camera": "Cameras",
    "other_electronics": "Other electronics",
}

# Reverse lookup for catalogue display labels already stored in SQLite.
DISPLAY_TO_CANONICAL = {
    **CATALOGUE_CATEGORY_MAP,
    "headphones / audio": "audio",
    "headphones/audio": "audio",
    "smart watches": "smartwatch_clocks",
    "other electronics": "other_electronics",
}

_FEATURE_STATEMENTS = (
    (
        ("most_frequent_previous_category",),
        "This category has appeared frequently in your purchasing history.",
        "category_frequency",
    ),
    (
        ("previous_category_proportion",),
        "This category has appeared frequently in your purchasing history.",
        "category_share",
    ),
    (
        ("previous_category_count",),
        "This category has appeared frequently in your purchasing history.",
        "category_count",
    ),
    (
        ("previous_category",),
        "Your previous purchases show interest in similar products.",
        "previous_category",
    ),
    (
        ("previous_brand",),
        "Your previous product and brand preferences also influenced the prediction.",
        "brand_preference",
    ),
    (
        ("previous_product",),
        "Your previous product and brand preferences also influenced the prediction.",
        "product_preference",
    ),
    (
        ("previous_orders_last_90_days", "previous_orders_last_30_days", "average_days_between_orders", "days_since_previous_order"),
        "Your recent purchasing pattern contributed to this prediction.",
        "recency",
    ),
    (
        (
            "previous_average_order_spend",
            "previous_average_item_price",
            "previous_min_order_spend",
            "previous_max_order_spend",
            "previous_total_spend",
        ),
        "Your previous spending pattern contributed to this prediction.",
        "spend",
    ),
    (
        ("history_order_count", "history_purchase_count", "previous_unique_product_count", "previous_unique_brand_count", "previous_category_diversity"),
        "Your overall purchasing history contributed to this prediction.",
        "history_volume",
    ),
)

_HIDDEN_FEATURE_TOKENS = (
    "user_id",
    "order_id",
    "category_id",
    "product_id",
    "previous_product",
    "__",
)


def canonical_category(value: Any) -> str | None:
    """Return the Phase 3 category label for a model or catalogue value."""
    return normalize_category(value) or DISPLAY_TO_CANONICAL.get(str(value or "").strip().lower())


def category_display_name(value: Any) -> str:
    """Return a customer-facing category name."""
    canonical = canonical_category(value)
    if canonical:
        return CATEGORY_DISPLAY_NAMES[canonical]
    text = str(value or "").strip()
    return text.replace("_", " ").title() if text else "Unknown"


def friendly_feature_name(feature: Any) -> str:
    """Translate an internal SHAP feature name into a short customer label."""
    cleaned = str(feature or "").strip().lower()
    if "most_frequent_previous_category" in cleaned:
        return "How often this category appears in your history"
    if "previous_category_proportion" in cleaned:
        return "Share of past purchases in this category"
    if "previous_category_count" in cleaned:
        return "How many times you bought this category"
    if cleaned == "previous_category" or cleaned.startswith("previous_category_"):
        return "Your previous purchase category"
    if "previous_brand" in cleaned:
        return "Your previous brand preference"
    if "previous_product" in cleaned:
        return "Your previous product preference"
    if "previous_average_order_spend" in cleaned:
        return "Typical amount spent per order"
    if "previous_average_item_price" in cleaned:
        return "Typical item price in your history"
    if "previous_min_order_spend" in cleaned:
        return "Lowest previous order spend"
    if "previous_max_order_spend" in cleaned:
        return "Highest previous order spend"
    if "previous_total_spend" in cleaned:
        return "Total previous spending"
    if "previous_orders_last_90_days" in cleaned:
        return "Purchases in the last 90 days"
    if "previous_orders_last_30_days" in cleaned:
        return "Purchases in the last 30 days"
    if "average_days_between_orders" in cleaned:
        return "Time between your purchases"
    if "days_since_previous_order" in cleaned:
        return "Time since your last purchase"
    if "history_order_count" in cleaned:
        return "Number of previous orders"
    if "history_purchase_count" in cleaned:
        return "Number of previous purchases"
    if "previous_unique_brand_count" in cleaned:
        return "Variety of brands in your history"
    if "previous_unique_product_count" in cleaned:
        return "Variety of products in your history"
    if "previous_category_diversity" in cleaned:
        return "Variety of categories in your history"
    return "Your purchasing history"


def friendly_feature_statement(feature: Any) -> str:
    """Return a customer-readable sentence supported by a SHAP feature."""
    cleaned = str(feature or "").strip().lower()
    for tokens, statement, _kind in _FEATURE_STATEMENTS:
        if any(token in cleaned for token in tokens):
            return statement
    return "Your purchasing history contributed to this prediction."


def _contributor_items(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    items = evidence.get("all_class_specific_contributions") or []
    if not items:
        items = list(evidence.get("top_positive_contributors") or []) + list(
            evidence.get("top_negative_contributors") or []
        )
    aggregated: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        feature = str(item.get("feature") or "")
        if not feature:
            continue
        try:
            weight = float(item.get("shap_value", item.get("weight", 0)))
        except (TypeError, ValueError):
            continue
        entry = aggregated.setdefault(feature, {"feature": feature, "shap_value": 0.0})
        entry["shap_value"] += weight
        if "feature_value" in item:
            entry["feature_value"] = item.get("feature_value")
    ranked = sorted(aggregated.values(), key=lambda row: abs(float(row["shap_value"])), reverse=True)
    return ranked


def shap_to_friendly_contributors(evidence: dict[str, Any], *, limit: int = 4) -> list[dict[str, Any]]:
    """Convert real SHAP contributors into customer-facing objects.

    Only features with a real non-zero SHAP value are included. Duplicate customer
    statements are collapsed so the UI does not repeat the same sentence.
    """
    seen_statements: set[str] = set()
    friendly: list[dict[str, Any]] = []
    for item in _contributor_items(evidence):
        weight = float(item["shap_value"])
        if weight == 0:
            continue
        statement = friendly_feature_statement(item["feature"])
        if statement in seen_statements:
            continue
        seen_statements.add(statement)
        friendly.append(
            {
                "feature": statement,
                "label": friendly_feature_name(item["feature"]),
                "direction": "positive" if weight > 0 else "negative",
                "weight": weight,
                "source_feature": item["feature"],
            }
        )
        if len(friendly) >= limit:
            break
    return friendly


def technical_shap_contributors(evidence: dict[str, Any], *, limit: int = 10) -> list[dict[str, Any]]:
    """Keep raw SHAP rows for the collapsible academic details panel."""
    rows = []
    for item in _contributor_items(evidence)[:limit]:
        rows.append(
            {
                "feature": item.get("feature"),
                "feature_value": item.get("feature_value"),
                "shap_value": float(item.get("shap_value", 0)),
                "direction": "positive" if float(item.get("shap_value", 0)) > 0 else "negative",
            }
        )
    return rows


def mentions_conflicting_category(text: str, predicted_canonical: str) -> bool:
    """True when generated text names a different canonical electronics category."""
    lowered = str(text or "").lower()
    predicted = canonical_category(predicted_canonical)
    if not predicted:
        return False
    predicted_display = category_display_name(predicted).lower()
    for canonical, display in CATEGORY_DISPLAY_NAMES.items():
        if canonical == predicted:
            continue
        tokens = {canonical, display.lower(), canonical.replace("_", " ")}
        if canonical == "laptop_notebook":
            tokens.update({"laptops", "laptop"})
        if canonical == "smartphone":
            tokens.update({"smartphones", "smartphone"})
        if any(token and token in lowered for token in tokens):
            # "electronics" is too generic to treat as a conflict with other_electronics.
            if canonical == "other_electronics" and "other" not in lowered:
                continue
            if display.lower() == predicted_display:
                continue
            return True
    return False


def customer_gemini_fallback(predicted_canonical: str, contributors: list[dict[str, Any]]) -> str:
    """Evidence-based plain-language explanation that never invents statistics."""
    display = category_display_name(predicted_canonical)
    positives = [item["feature"] for item in contributors if item.get("direction") == "positive"][:3]
    if not positives:
        return (
            f"The AI predicted {display} because your purchasing history shows a stronger pattern "
            "of interest in this category. This is a model association, not a guaranteed purchase."
        )
    reasons = " ".join(positives)
    return (
        f"The AI predicted {display} because your purchasing history shows a stronger pattern of "
        f"interest in this category. {reasons} This is a model association, not a guaranteed purchase."
    )


def sanitize_customer_text(text: str, predicted_canonical: str, contributors: list[dict[str, Any]]) -> str:
    """Keep Gemini wording only when it explains the same predicted category."""
    cleaned = str(text or "").strip()
    predicted = canonical_category(predicted_canonical) or str(predicted_canonical)
    display = category_display_name(predicted)
    if not cleaned or mentions_conflicting_category(cleaned, predicted):
        return customer_gemini_fallback(predicted, contributors)
    replacements = {
        "other_electronics": display if predicted == "other_electronics" else "other electronics",
        "laptop_notebook": "Laptops" if predicted == "laptop_notebook" else "laptops",
        "smartwatch_clocks": "Smart Watches" if predicted == "smartwatch_clocks" else "smart watches",
        "computer_peripherals": "Computer Peripherals",
        "computer_components": "Computer Components",
    }
    for raw, label in replacements.items():
        cleaned = cleaned.replace(raw, label)
    for token in _HIDDEN_FEATURE_TOKENS:
        if token in cleaned:
            return customer_gemini_fallback(predicted, contributors)
    return cleaned
