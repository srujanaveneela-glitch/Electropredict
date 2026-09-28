"""Chunked Pandas preprocessing for the ElectroPredict purchase dataset."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from pathlib import Path

import pandas as pd

EXPECTED_COLUMNS = [
    "event_time",
    "order_id",
    "product_id",
    "category_id",
    "category_code",
    "brand",
    "price",
    "user_id",
]
NUMERIC_CATEGORY_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")
EXPECTED_START_UTC = pd.Timestamp("2020-01-01", tz="UTC")
EXPECTED_END_UTC = pd.Timestamp("2021-01-01", tz="UTC")


def category_to_target(category_code: object) -> str | None:
    """Map a real category_code to an electronics target group."""
    if pd.isna(category_code):
        return None
    value = str(category_code).strip().lower()
    if not value or NUMERIC_CATEGORY_RE.fullmatch(value):
        return None

    if value == "electronics.smartphone" or value.startswith("electronics.smartphone."):
        return "smartphone"
    if value == "computers.notebook" or value.startswith("computers.notebook."):
        return "laptop_notebook"
    if value == "electronics.tablet" or value.startswith("electronics.tablet."):
        return "tablet"
    if value.startswith("electronics.audio."):
        return "audio"
    if value.startswith("electronics.video."):
        return "video"
    if value == "electronics.clocks" or value.startswith("electronics.clocks."):
        return "smartwatch_clocks"
    if value.startswith("electronics.camera."):
        return "camera"
    if value == "electronics.telephone" or value.startswith("electronics.telephone."):
        return "telephone"
    if value == "computers.desktop" or value.startswith("computers.desktop."):
        return "desktop"
    if value.startswith("computers.peripherals."):
        return "computer_peripherals"
    if value.startswith("computers.components."):
        return "computer_components"
    if value == "computers.gaming" or value.startswith("computers.gaming."):
        return "gaming"
    if value.startswith("electronics.") or value.startswith("computers."):
        return "other_electronics"
    return None


def electronics_target_series(category_codes: pd.Series) -> pd.Series:
    """Return target labels, with missing labels marking non-electronics rows."""
    return category_codes.map(category_to_target).astype("string")


def is_numeric_category_code(category_codes: pd.Series) -> pd.Series:
    """Identify numeric-looking category codes that are invalid category labels."""
    values = category_codes.astype("string").str.strip()
    return values.notna() & values.str.fullmatch(NUMERIC_CATEGORY_RE.pattern, na=False)


def clean_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """Normalize fields and derive quality flags without inventing values."""
    result = chunk.copy()
    for column in ("category_code", "brand", "user_id"):
        result[column] = result[column].astype("string").str.strip()
        result[column] = result[column].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    result["event_time_parsed"] = pd.to_datetime(
        result["event_time"], errors="coerce", utc=True
    )
    result["valid_event_time"] = result["event_time_parsed"].between(
        EXPECTED_START_UTC, EXPECTED_END_UTC, inclusive="left"
    )
    result["price_numeric"] = pd.to_numeric(result["price"], errors="coerce")
    result["numeric_category_code"] = is_numeric_category_code(result["category_code"])
    result["prediction_category"] = electronics_target_series(result["category_code"])
    result["usable_electronics"] = (
        result["user_id"].notna()
        & result["category_code"].notna()
        & ~result["numeric_category_code"]
        & result["valid_event_time"]
        & result["price_numeric"].gt(0)
        & result["prediction_category"].notna()
    )
    return result


def read_purchase_chunks(
    csv_path: str | Path,
    chunksize: int = 100_000,
    on_bad_line: Callable[[list[str]], None] | None = None,
) -> Iterator[pd.DataFrame]:
    """Read the CSV with Pandas in bounded chunks and the expected schema."""
    yield from pd.read_csv(
        csv_path,
        usecols=EXPECTED_COLUMNS,
        dtype={column: "string" for column in EXPECTED_COLUMNS},
        chunksize=chunksize,
        engine="python",
        on_bad_lines=on_bad_line or "error",
    )
