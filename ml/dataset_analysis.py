"""Run the Phase 1 dataset analysis in one chunked Pandas pass."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from preprocessing import clean_chunk, read_purchase_chunks


def row_hashes(chunk: pd.DataFrame) -> pd.Series:
    """Hash parsed records so duplicate investigation uses parsed fields."""
    columns = [
        "event_time",
        "order_id",
        "product_id",
        "category_id",
        "category_code",
        "brand",
        "price",
        "user_id",
    ]
    return pd.util.hash_pandas_object(chunk[columns], index=False)


def analyze_dataset(csv_path: Path, chunksize: int = 100_000) -> dict:
    bad_rows = 0

    def count_bad_line(_line: list[str]) -> None:
        nonlocal bad_rows
        bad_rows += 1

    counters = Counter()
    category_counts = Counter()
    category_original_values: dict[str, Counter] = {}
    category_code_counts = Counter()
    duplicate_hashes: set[int] = set()
    duplicate_rows = 0
    min_date = None
    max_date = None
    usable_users: set[str] = set()

    for chunk in read_purchase_chunks(csv_path, chunksize, on_bad_line=count_bad_line):
        counters["valid_rows_parsed"] += len(chunk)
        hashes = row_hashes(chunk)
        for value in hashes.tolist():
            hash_value = int(value)
            if hash_value in duplicate_hashes:
                duplicate_rows += 1
            else:
                duplicate_hashes.add(hash_value)

        cleaned = clean_chunk(chunk)
        counters["missing_user_id"] += int(cleaned["user_id"].isna().sum())
        counters["missing_category_code"] += int(cleaned["category_code"].isna().sum())
        counters["missing_brand"] += int(cleaned["brand"].isna().sum())
        counters["missing_or_invalid_price"] += int(cleaned["price_numeric"].isna().sum())
        counters["non_positive_price"] += int(cleaned["price_numeric"].le(0).sum())
        counters["invalid_dates"] += int((~cleaned["valid_event_time"]).sum())
        counters["numeric_category_code"] += int(cleaned["numeric_category_code"].sum())

        valid_categories = cleaned["category_code"].dropna().astype(str)
        category_code_counts.update(valid_categories.tolist())
        mapped = cleaned.loc[cleaned["usable_electronics"], ["prediction_category", "category_code"]]
        category_counts.update(mapped["prediction_category"].astype(str).tolist())
        for target, code in zip(mapped["prediction_category"], mapped["category_code"]):
            category_original_values.setdefault(str(target), Counter())[str(code)] += 1

        usable_times = cleaned.loc[cleaned["usable_electronics"], "event_time_parsed"]
        if not usable_times.empty:
            chunk_min = usable_times.min()
            chunk_max = usable_times.max()
            min_date = chunk_min if min_date is None else min(min_date, chunk_min)
            max_date = chunk_max if max_date is None else max(max_date, chunk_max)
        usable_users.update(cleaned.loc[cleaned["usable_electronics"], "user_id"].astype(str))
        counters["valid_electronics_rows"] += int(cleaned["usable_electronics"].sum())

    raw_rows = counters["valid_rows_parsed"] + bad_rows
    electronics_rows = counters["valid_electronics_rows"]
    category_distribution = []
    for target, count in sorted(category_counts.items(), key=lambda item: (-item[1], item[0])):
        category_distribution.append(
            {
                "target_category": target,
                "record_count": count,
                "percentage_of_usable_electronics": round(100 * count / electronics_rows, 4),
                "original_category_codes": [
                    {"category_code": code, "record_count": value}
                    for code, value in category_original_values[target].most_common()
                ],
            }
        )

    return {
        "dataset_path": str(csv_path),
        "raw_rows_processed": raw_rows,
        "valid_rows_parsed_by_pandas": counters["valid_rows_parsed"],
        "pandas_bad_records": bad_rows,
        "quality_counts": {
            "missing_user_id": counters["missing_user_id"],
            "missing_category_code": counters["missing_category_code"],
            "missing_brand": counters["missing_brand"],
            "missing_or_invalid_price": counters["missing_or_invalid_price"],
            "non_positive_price": counters["non_positive_price"],
            "invalid_dates": counters["invalid_dates"],
            "numeric_category_code": counters["numeric_category_code"],
            "exact_duplicate_rows_after_parsing": duplicate_rows,
        },
        "electronics_filter": {
            "valid_electronics_rows": electronics_rows,
            "excluded_non_electronics_or_unusable_rows": counters["valid_rows_parsed"] - electronics_rows,
            "usable_unique_users": len(usable_users),
            "usable_date_range_utc": {
                "min": min_date.isoformat() if min_date is not None else None,
                "max": max_date.isoformat() if max_date is not None else None,
            },
        },
        "category_distribution": category_distribution,
        "top_observed_category_codes": [
            {"category_code": code, "record_count": count}
            for code, count in category_code_counts.most_common(100)
        ],
        "target_design": {
            "target": "next_purchase_category",
            "rare_class_threshold_records": 100,
            "rare_class_policy": "Review classes below the threshold; merge defensible electronic classes into other_electronics or exclude them from a stable multiclass target.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=Path(__file__).parents[1] / "electropredict.csv")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "reports" / "phase1_analysis.json")
    parser.add_argument("--chunksize", type=int, default=100_000)
    args = parser.parse_args()
    report = analyze_dataset(args.csv, args.chunksize)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
