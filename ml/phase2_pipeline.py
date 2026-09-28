"""Build and validate the leakage-safe Phase 2 training dataset.

This script is intentionally offline. It does not train a model or touch the Flask app.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from feature_engineering import (
    aggregate_electronics_orders,
    build_next_order_samples,
    merge_rare_target_categories,
)
from preprocessing import read_purchase_chunks, clean_chunk


DEFAULT_CSV = Path(__file__).parents[1] / "electropredict.csv"
DEFAULT_OUTPUT = Path(__file__).parent / "data" / "phase2_training.csv.gz"
DEFAULT_REPORT = Path(__file__).parent / "reports" / "phase2_validation.json"
AUDIT_COLUMNS = [
    "history_end_order_id",
    "history_end_timestamp",
    "target_order_id",
    "prediction_timestamp",
]
TARGET_ORDER_COLUMNS = {
    "target_order_id",
    "prediction_timestamp",
    "next_purchase_category",
}


def load_usable_electronics(csv_path: Path, chunksize: int) -> tuple[pd.DataFrame, dict]:
    """Read the original CSV once and retain only Phase 1-usable columns."""
    bad_records = 0
    parsed_rows = 0
    chunks = []

    def count_bad_line(_line: list[str]) -> None:
        nonlocal bad_records
        bad_records += 1

    for chunk in read_purchase_chunks(csv_path, chunksize, on_bad_line=count_bad_line):
        parsed_rows += len(chunk)
        cleaned = clean_chunk(chunk)
        usable = cleaned.loc[cleaned["usable_electronics"]].copy()
        if not usable.empty:
            chunks.append(
                usable[
                    [
                        "event_time",
                        "order_id",
                        "product_id",
                        "category_id",
                        "category_code",
                        "brand",
                        "price",
                        "user_id",
                        "event_time_parsed",
                        "price_numeric",
                        "prediction_category",
                    ]
                ]
            )

    if not chunks:
        raise ValueError("No usable electronics rows were found in the dataset.")
    events = pd.concat(chunks, ignore_index=True)
    return events, {
        "valid_pandas_rows": parsed_rows,
        "valid_electronics_rows": int(len(events)),
        "pandas_bad_records": bad_records,
    }


def build_phase2_dataset(
    csv_path: Path,
    output_path: Path,
    report_path: Path,
    chunksize: int = 100_000,
    rare_threshold: int = 100,
) -> dict:
    """Build the derived training dataset and return its validation report."""
    events, read_metadata = load_usable_electronics(csv_path, chunksize)
    orders, order_metadata = aggregate_electronics_orders(events)
    provisional_orders = orders.assign(final_order_category=orders["order_category"])
    provisional_categories = sorted(provisional_orders["final_order_category"].dropna().unique().tolist())
    provisional_samples, _, _ = build_next_order_samples(provisional_orders, provisional_categories)
    orders, category_metadata = merge_rare_target_categories(
        orders, provisional_samples, rare_threshold
    )
    category_names = sorted(orders["final_order_category"].dropna().unique().tolist())
    samples, feature_columns, sample_metadata = build_next_order_samples(orders, category_names)

    if samples.empty:
        raise ValueError("No supervised samples were produced; inspect order history and filters.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    samples.to_csv(output_path, index=False, compression="infer")

    target_counts = samples["next_purchase_category"].value_counts().sort_index()
    target_total = int(target_counts.sum())
    feature_missing = samples[feature_columns].isna().sum()
    audit_columns_excluded = all(column not in feature_columns for column in AUDIT_COLUMNS)
    target_order_columns_excluded = all(column not in feature_columns for column in TARGET_ORDER_COLUMNS)
    history_before_target = (
        (samples["history_end_timestamp"] < samples["prediction_timestamp"])
        | (
            (samples["history_end_timestamp"] == samples["prediction_timestamp"])
            & (samples["history_end_order_id"] < samples["target_order_id"])
        )
    )
    exact_identity_columns = [
        "user_id",
        "history_end_order_id",
        "history_end_timestamp",
        "target_order_id",
        "prediction_timestamp",
        "next_purchase_category",
    ]
    feature_signature_columns = feature_columns + ["next_purchase_category"]
    exact_identity_duplicates = int(samples.duplicated(subset=exact_identity_columns).sum())
    feature_signature_duplicates = int(samples.duplicated(subset=feature_signature_columns).sum())
    report = {
        "dataset_path": str(csv_path),
        "output_path": str(output_path),
        "read_metadata": read_metadata,
        "valid_electronics_orders": int(len(orders)),
        "users_considered": sample_metadata["users_considered"],
        "users_with_at_least_two_electronics_orders": sample_metadata[
            "users_with_at_least_two_electronics_orders"
        ],
        "supervised_prediction_samples": sample_metadata["supervised_prediction_samples"],
        "samples_removed_no_future_purchase": sample_metadata["samples_removed_no_future_purchase"],
        "samples_removed_insufficient_history": sample_metadata[
            "samples_removed_insufficient_history"
        ],
        "order_level_metadata": order_metadata,
        "target_category_decision": category_metadata,
        "final_target_categories": category_names,
        "target_distribution": [
            {
                "category": category,
                "count": int(count),
                "percentage": round(100 * int(count) / target_total, 4),
            }
            for category, count in target_counts.items()
        ],
        "feature_column_count": len(feature_columns),
        "feature_columns": feature_columns,
        "audit_columns": AUDIT_COLUMNS,
        "audit_columns_excluded_from_features": audit_columns_excluded,
        "target_order_columns_excluded_from_features": target_order_columns_excluded,
        "missing_values_in_final_features": {
            column: int(value) for column, value in feature_missing.items() if value
        },
        "duplicate_training_samples": exact_identity_duplicates,
        "exact_duplicate_supervised_samples": exact_identity_duplicates,
        "repeated_feature_signature_rows": feature_signature_duplicates,
        "duplicate_investigation": {
            "exact_identity_columns": exact_identity_columns,
            "feature_signature_columns_exclude_user_and_audit_identity": True,
            "interpretation": "Repeated feature signatures with distinct user/order audit identity are legitimate repeated historical states; exact identity duplicates are duplicate supervised samples.",
        },
        "prediction_timestamp_range": {
            "earliest": samples["prediction_timestamp"].min().isoformat(),
            "latest": samples["prediction_timestamp"].max().isoformat(),
        },
        "features_only_before_target_purchase": bool(history_before_target.all()),
        "no_target_order_information_in_features": target_order_columns_excluded,
        "remaining_data_quality_concerns": [
            "The primary category of a multi-category order is selected by line count, then spend, then category name.",
            "A minimum history of one complete electronics order is required; users with one order have no supervised sample.",
            "Rare order categories below the configured threshold are merged into other_electronics.",
            "Categorical history fields are retained as strings for later model preprocessing.",
        ],
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--chunksize", type=int, default=100_000)
    parser.add_argument("--rare-threshold", type=int, default=100)
    args = parser.parse_args()
    report = build_phase2_dataset(
        args.csv,
        args.output,
        args.report,
        chunksize=args.chunksize,
        rare_threshold=args.rare_threshold,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
