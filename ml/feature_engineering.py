"""Leakage-safe order aggregation and feature construction for Phase 2."""

from __future__ import annotations

from collections import Counter

import pandas as pd

FEATURE_DEFINITIONS = {
    "history_order_count": "Number of complete electronics orders before the target order.",
    "history_purchase_count": "Number of usable electronics order records before the target order.",
    "previous_total_spend": "Sum of order spending before the target order.",
    "previous_average_order_spend": "Mean order spending before the target order.",
    "previous_min_order_spend": "Minimum order spending before the target order.",
    "previous_max_order_spend": "Maximum order spending before the target order.",
    "previous_average_item_price": "Mean item price across prior order lines.",
    "previous_unique_product_count": "Distinct products in prior orders.",
    "previous_unique_brand_count": "Distinct non-missing brands in prior orders.",
    "days_since_previous_order": "Days since the immediately preceding historical order.",
    "average_days_between_orders": "Mean gap between historical order timestamps.",
    "previous_category_diversity": "Distinct primary order categories in history.",
    "previous_category_counts": "Count of each primary category in history.",
    "previous_category_proportions": "Category counts divided by historical order count.",
    "previous_category": "Primary category of the latest historical order.",
    "most_frequent_previous_category": "Most frequent historical primary category.",
    "previous_brand": "Deterministic first brand from the latest historical order.",
    "previous_product": "Deterministic first product from the latest historical order.",
    "previous_orders_last_30_days": "Historical order count in the preceding 30 days.",
    "previous_orders_last_90_days": "Historical order count in the preceding 90 days.",
}


def aggregate_electronics_orders(events: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Create one chronological record per customer electronics order."""
    required = {
        "user_id",
        "order_id",
        "event_time_parsed",
        "prediction_category",
        "product_id",
        "brand",
        "price_numeric",
    }
    missing = required.difference(events.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    usable = events.loc[events["order_id"].notna()].copy()
    usable["order_id"] = usable["order_id"].astype("string").str.strip()
    usable = usable.loc[usable["order_id"].notna() & usable["order_id"].ne("")]
    usable = usable.drop_duplicates(
        subset=[
            "event_time",
            "order_id",
            "product_id",
            "category_id",
            "category_code",
            "brand",
            "price",
            "user_id",
        ]
    )

    category_stats = (
        usable.groupby(["user_id", "order_id", "prediction_category"], dropna=False)
        .agg(category_line_count=("product_id", "size"), category_spend=("price_numeric", "sum"))
        .reset_index()
        .sort_values(
            ["user_id", "order_id", "category_line_count", "category_spend", "prediction_category"],
            ascending=[True, True, False, False, True],
        )
    )
    primary_categories = category_stats.drop_duplicates(["user_id", "order_id"])[
        ["user_id", "order_id", "prediction_category"]
    ].rename(columns={"prediction_category": "order_category"})

    ordered_lines = usable.sort_values(["user_id", "order_id", "product_id", "brand"])
    first_line = ordered_lines.drop_duplicates(["user_id", "order_id"])[
        ["user_id", "order_id", "product_id", "brand"]
    ].rename(columns={"product_id": "first_product", "brand": "first_brand"})

    orders = (
        usable.groupby(["user_id", "order_id"], dropna=False)
        .agg(
            event_time=("event_time_parsed", "min"),
            order_total_spend=("price_numeric", "sum"),
            order_average_item_price=("price_numeric", "mean"),
            order_unique_product_count=("product_id", "nunique"),
            order_line_count=("product_id", "size"),
            order_products=("product_id", lambda values: tuple(sorted(set(values.dropna().astype(str))))),
            order_brands=("brand", lambda values: tuple(sorted(set(values.dropna().astype(str))))),
        )
        .reset_index()
        .merge(primary_categories, on=["user_id", "order_id"], how="left", validate="one_to_one")
        .merge(first_line, on=["user_id", "order_id"], how="left", validate="one_to_one")
        .sort_values(["user_id", "event_time", "order_id"])
        .reset_index(drop=True)
    )
    multi_category_orders = int(
        category_stats.groupby(["user_id", "order_id"], sort=False).size().gt(1).sum()
    )
    return orders, {
        "deduplicated_electronics_rows": len(usable),
        "exact_duplicate_electronics_rows_removed": len(events) - len(usable),
        "multi_category_orders": multi_category_orders,
    }


def merge_rare_target_categories(
    orders: pd.DataFrame,
    target_samples: pd.DataFrame,
    minimum_target_count: int = 100,
) -> tuple[pd.DataFrame, dict]:
    """Merge categories whose future-target count is below the stability threshold."""
    raw_counts = orders["order_category"].value_counts().sort_index()
    target_counts = target_samples["next_purchase_category"].value_counts().sort_index()
    rare = target_counts[target_counts < minimum_target_count].index.tolist()
    final = orders.copy()
    final["final_order_category"] = final["order_category"].where(
        ~final["order_category"].isin(rare), "other_electronics"
    )
    return final, {
        "minimum_target_count": minimum_target_count,
        "raw_order_category_counts": {str(key): int(value) for key, value in raw_counts.items()},
        "raw_target_category_counts": {str(key): int(value) for key, value in target_counts.items()},
        "rare_categories_merged": [str(value) for value in rare if value != "other_electronics"],
        "final_order_category_counts": {
            str(key): int(value)
            for key, value in final["final_order_category"].value_counts().sort_index().items()
        },
    }


def build_next_order_samples(
    orders: pd.DataFrame, category_names: list[str]
) -> tuple[pd.DataFrame, list[str], dict]:
    """Build samples whose features end before and target is the next order."""
    feature_rows = []
    users_considered = 0
    users_with_future_order = 0
    no_future_purchase = 0
    insufficient_history = 0

    for user_id, user_orders in orders.groupby("user_id", sort=False):
        history_orders = user_orders.sort_values(["event_time", "order_id"]).reset_index(drop=True)
        users_considered += 1
        no_future_purchase += 1
        if len(history_orders) < 2:
            continue
        users_with_future_order += 1
        category_counts = Counter()
        product_values = set()
        brand_values = set()
        prior_times = []
        total_spend = 0.0
        interval_total_days = 0.0
        interval_count = 0

        for position in range(len(history_orders) - 1):
            current = history_orders.iloc[position]
            target = history_orders.iloc[position + 1]
            history_count = position + 1
            if history_count < 1:
                insufficient_history += 1
                continue

            current_time = current["event_time"]
            target_time = target["event_time"]
            gaps = [(current_time - prior_time).total_seconds() / 86400 for prior_time in prior_times]
            category_counts[current["final_order_category"]] += 1
            product_values.update(current["order_products"])
            brand_values.update(current["order_brands"])
            if prior_times:
                interval_total_days += gaps[-1]
                interval_count += 1
            prior_times.append(current_time)
            total_spend += float(current["order_total_spend"])

            recent_30 = sum((target_time - prior_time).total_seconds() <= 30 * 86400 for prior_time in prior_times)
            recent_90 = sum((target_time - prior_time).total_seconds() <= 90 * 86400 for prior_time in prior_times)
            most_frequent = sorted(category_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
            row = {
                "user_id": user_id,
                "target_order_id": target["order_id"],
                "prediction_timestamp": target["event_time"],
                "history_end_order_id": current["order_id"],
                "history_end_timestamp": current["event_time"],
                "next_purchase_category": target["final_order_category"],
                "history_order_count": history_count,
                "history_purchase_count": history_count,
                "previous_total_spend": total_spend,
                "previous_average_order_spend": total_spend / history_count,
                "previous_min_order_spend": float(history_orders.iloc[:history_count]["order_total_spend"].min()),
                "previous_max_order_spend": float(history_orders.iloc[:history_count]["order_total_spend"].max()),
                "previous_average_item_price": float(history_orders.iloc[:history_count]["order_average_item_price"].mean()),
                "previous_unique_product_count": len(product_values),
                "previous_unique_brand_count": len(brand_values),
                "days_since_previous_order": gaps[-1] if gaps else 0.0,
                "average_days_between_orders": interval_total_days / interval_count if interval_count else 0.0,
                "previous_category_diversity": len(category_counts),
                "previous_category": current["final_order_category"],
                "most_frequent_previous_category": most_frequent,
                "previous_brand": current["first_brand"],
                "previous_product": current["first_product"],
                "previous_orders_last_30_days": recent_30,
                "previous_orders_last_90_days": recent_90,
            }
            for category in category_names:
                count = category_counts.get(category, 0)
                row[f"previous_category_count__{category}"] = count
                row[f"previous_category_proportion__{category}"] = count / history_count
            feature_rows.append(row)

    samples = pd.DataFrame(feature_rows)
    feature_columns = [
        column
        for column in samples.columns
        if column
        not in {
            "user_id",
            "target_order_id",
            "prediction_timestamp",
            "history_end_order_id",
            "history_end_timestamp",
            "next_purchase_category",
        }
    ]
    numeric_columns = samples[feature_columns].select_dtypes(include="number").columns
    categorical_columns = [column for column in feature_columns if column not in numeric_columns]
    samples[numeric_columns] = samples[numeric_columns].fillna(0)
    samples[categorical_columns] = samples[categorical_columns].fillna("__missing__")
    metadata = {
        "users_considered": users_considered,
        "users_with_at_least_two_electronics_orders": users_with_future_order,
        "supervised_prediction_samples": len(samples),
        "samples_removed_no_future_purchase": no_future_purchase,
        "samples_removed_insufficient_history": insufficient_history,
    }
    return samples, feature_columns, metadata
