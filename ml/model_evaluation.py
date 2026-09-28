"""Evaluation helpers for the Phase 3 temporal classification experiment."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)


def evaluate_classifier(
    model,
    x_test: pd.DataFrame,
    y_test: pd.Series,
    labels: Sequence[str],
    output_dir: Path,
) -> dict:
    """Evaluate only on the supplied chronological holdout and save artifacts."""
    predictions = model.predict(x_test)
    label_list = list(labels)
    report = classification_report(
        y_test,
        predictions,
        labels=label_list,
        output_dict=True,
        zero_division=0,
    )
    confusion = confusion_matrix(y_test, predictions, labels=label_list)
    majority_class = y_test.value_counts().index[0]

    pd.DataFrame(confusion, index=label_list, columns=label_list).to_csv(
        output_dir / "confusion_matrix.csv", index_label="actual"
    )
    metrics = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "macro_f1": float(f1_score(y_test, predictions, labels=label_list, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_test, predictions, labels=label_list, average="weighted", zero_division=0)),
        "majority_class": str(majority_class),
        "majority_baseline_accuracy": float((y_test == majority_class).mean()),
        "test_samples": int(len(y_test)),
        "classification_report": report,
        "class_labels": label_list,
    }
    return metrics


def save_classification_report(metrics: dict, output_dir: Path) -> None:
    """Save the per-class report separately for convenient inspection."""
    report = metrics["classification_report"]
    rows = []
    for label, values in report.items():
        if isinstance(values, dict):
            rows.append({"class": label, **values})
    pd.DataFrame(rows).to_csv(output_dir / "classification_report.csv", index=False)
