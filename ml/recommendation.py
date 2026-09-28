"""
Product-specific electronics recommendations.

This module is a recommendation/selection layer only.

The existing Phase 3 Random Forest prediction is still responsible for
predicting the category. This module does NOT train or modify the ML model,
SHAP explanation, or Gemini explanation.

The recommendation process is:

1. Receive the predicted category.
2. Receive the currently selected product.
3. Keep products belonging to the predicted category.
4. Exclude the currently selected product.
5. Calculate product-to-product similarity using catalogue attributes.
6. Return the most similar products.

This makes recommendations vary from product to product while preserving
the predicted-category constraint.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any
import math


SUPPORTED_CATEGORIES = frozenset(
    {
        "smartphone",
        "laptop_notebook",
        "tablet",
        "smartwatch_clocks",
        "audio",
        "video",
        "computer_peripherals",
        "computer_components",
        "telephone",
        "desktop",
        "camera",
        "other_electronics",
    }
)


CATALOGUE_CATEGORY_MAP = {
    "smartphone": "smartphone",
    "smartphones": "smartphone",

    "laptop_notebook": "laptop_notebook",
    "laptops": "laptop_notebook",
    "laptop": "laptop_notebook",
    "notebooks": "laptop_notebook",

    "tablet": "tablet",
    "tablets": "tablet",

    "smartwatch_clocks": "smartwatch_clocks",
    "smart watches": "smartwatch_clocks",
    "smartwatch": "smartwatch_clocks",

    "audio": "audio",
    "headphones": "audio",

    "video": "video",

    "computer_peripherals": "computer_peripherals",
    "computer peripherals": "computer_peripherals",

    "computer components": "computer_components",
    "computer_components": "computer_components",

    "other electronics": "other_electronics",
    "other_electronics": "other_electronics",

    "telephone": "telephone",
    "telephones": "telephone",

    "desktop": "desktop",
    "desktops": "desktop",

    "camera": "camera",
    "cameras": "camera",
}


def normalize_category(category: Any) -> str | None:
    """Return a supported canonical category, or None."""
    value = str(category).strip().lower() if category is not None else ""
    return CATALOGUE_CATEGORY_MAP.get(value)


def _number(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    try:
        number = float(value)
        if math.isfinite(number):
            return number
    except (TypeError, ValueError):
        pass

    return default


def _text(value: Any) -> str:
    """Return normalized lowercase text."""
    return str(value or "").strip().lower()


def _price_similarity(
    source_price: float,
    candidate_price: float,
) -> float:
    """
    Return price similarity between 0 and 1.

    Products with similar prices receive a higher score.
    """
    if source_price <= 0 or candidate_price <= 0:
        return 0.5

    difference = abs(source_price - candidate_price)

    average = (source_price + candidate_price) / 2

    if average <= 0:
        return 0.5

    ratio = difference / average

    return max(0.0, 1.0 - ratio)


def _rating_similarity(
    source_rating: float,
    candidate_rating: float,
) -> float:
    """
    Return rating similarity between 0 and 1.
    """
    difference = abs(source_rating - candidate_rating)

    return max(0.0, 1.0 - (difference / 5.0))


def _product_similarity(
    source_product: Mapping[str, Any],
    candidate_product: Mapping[str, Any],
) -> float:
    """
    Calculate a product-specific similarity score.

    Category is already guaranteed to match before this function is called.

    Scoring:
        category : 40%
        brand    : 25%
        price    : 25%
        rating   : 10%

    Category receives the strongest weight because recommendations must
    remain within the predicted electronics category.
    """

    source_category = normalize_category(
        source_product.get("category")
    )

    candidate_category = normalize_category(
        candidate_product.get("category")
    )

    category_score = (
        1.0
        if source_category == candidate_category
        else 0.0
    )

    source_brand = _text(
        source_product.get("brand")
    )

    candidate_brand = _text(
        candidate_product.get("brand")
    )

    brand_score = (
        1.0
        if source_brand
        and candidate_brand
        and source_brand == candidate_brand
        else 0.0
    )

    source_price = _number(
        source_product.get("price")
    )

    candidate_price = _number(
        candidate_product.get("price")
    )

    price_score = _price_similarity(
        source_price,
        candidate_price,
    )

    source_rating = _number(
        source_product.get("rating")
    )

    candidate_rating = _number(
        candidate_product.get("rating")
    )

    rating_score = _rating_similarity(
        source_rating,
        candidate_rating,
    )

    score = (
        category_score * 0.40
        + brand_score * 0.25
        + price_score * 0.25
        + rating_score * 0.10
    )

    return score


def recommend_products(
    predicted_category: str,
    products: Iterable[Mapping[str, Any]],
    *,
    selected_product: Mapping[str, Any] | None = None,
    exclude_product_id: int | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """
    Return product-specific recommendations.

    The Random Forest predicted category remains the category constraint.

    If selected_product is supplied, recommendations are ranked according
    to similarity with that exact product.

    The current product is always excluded.
    """

    canonical_category = normalize_category(
        predicted_category
    )

    if canonical_category not in SUPPORTED_CATEGORIES:
        raise ValueError(
            "predicted_category must be a supported electronics category."
        )

    if not isinstance(limit, int) or not 1 <= limit <= 50:
        raise ValueError(
            "limit must be an integer between 1 and 50."
        )

    if exclude_product_id is not None:
        try:
            exclude_product_id = int(
                exclude_product_id
            )
        except (TypeError, ValueError):
            exclude_product_id = None

    all_products = [
        dict(product)
        for product in products
        if product.get("is_active", 1)
    ]

    # ---------------------------------------------------------
    # Keep only products from the predicted electronics category
    # ---------------------------------------------------------

    matches = [
        product
        for product in all_products
        if normalize_category(
            product.get("category")
        ) == canonical_category
    ]

    # ---------------------------------------------------------
    # Exclude currently opened product
    # ---------------------------------------------------------

    if exclude_product_id is not None:
        matches = [
            product
            for product in matches
            if int(product.get("id") or 0)
            != exclude_product_id
        ]

    # ---------------------------------------------------------
    # Product-specific ranking
    # ---------------------------------------------------------

    if selected_product:

        for product in matches:
            product["_similarity_score"] = _product_similarity(
                selected_product,
                product,
            )

        matches.sort(
            key=lambda product: (
                -float(
                    product.get(
                        "_similarity_score",
                        0
                    )
                ),
                -_number(product.get("rating")),
                -_number(product.get("review_count")),
                _number(product.get("price")),
                int(product.get("id") or 0),
            )
        )

    else:
        # Fallback ranking if no selected product is supplied.
        matches.sort(
            key=lambda product: (
                -_number(product.get("rating")),
                -_number(product.get("review_count")),
                _number(product.get("price")),
                int(product.get("id") or 0),
            )
        )

    # ---------------------------------------------------------
    # Remove internal similarity field from API response
    # ---------------------------------------------------------

    selected_matches = matches[:limit]

    for product in selected_matches:
        product.pop("_similarity_score", None)

    return {
        "input": {
            "predicted_category": predicted_category,
            "selected_product_id": (
                int(selected_product.get("id"))
                if selected_product
                and selected_product.get("id") is not None
                else exclude_product_id
            ),
        },

        "predicted_category": canonical_category,

        "product_source": (
            "active products in the ElectroPredict "
            "application catalogue"
        ),

        "selection": {
            "electronics_only": True,
            "product_specific": bool(selected_product),
            "ranking": [
                "category_match",
                "brand_similarity",
                "price_similarity",
                "rating_similarity",
            ],
            "limit": limit,
        },

        "products": selected_matches,
    }