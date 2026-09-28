# ElectroPredict ML preparation

This directory contains the offline data-preparation stages for the research project. Phase 2 does not train a model, calculate SHAP values, call Generative AI, create recommendations, change Flask, change SQLite, or modify `electropredict.csv`.

## Core electronics recommendation system

`recommendation.py` is a deterministic selection layer after Phase 3. Its input
is the `predicted_category` emitted by the saved Phase 3 Random Forest, not a
Gemini response. The Flask `POST /api/recommendations` endpoint passes that
category to the selector and reads products from active rows in the existing
ElectroPredict SQLite `products` table. No product is generated or copied from
the dataset at recommendation time.

The selector normalizes the application's display labels (for example,
`Smartphones` and `Laptops`) to the existing canonical electronics categories.
It rejects unsupported categories, excludes inactive or unmapped rows, and
returns only products matching the predicted category. Products are ranked
transparently by rating descending, review count descending, price ascending,
then product ID ascending. The JSON output includes the canonical predicted
category, product source, selection rules, and the actual catalogue product
records. Gemini is not called and cannot alter the category or product fields.

Example request body: `{"predicted_category": "smartphone", "limit": 5}`.

## Phase 2 objective

Given a customer's electronics purchase history, predict the category of that customer's next electronics purchase order. The target is a future order category, not a product ID and not a category from the same order as the history.

## Order-level temporal methodology

`phase2_pipeline.py` reads the original CSV once with Pandas in chunks and reuses the Phase 1 filtering in `preprocessing.py`. Rows are retained only when they have a usable user ID, valid 2020 UTC timestamp, positive numeric price, valid non-numeric electronics category, and a Phase 1 category mapping.

Exact duplicate parsed transaction rows are removed. Remaining electronics lines are grouped by `(user_id, order_id)` into one electronics order. An order timestamp is its earliest line timestamp. For multi-category orders, the primary category is selected by greatest line count, then greatest category spend, then alphabetically first category name.

Orders are sorted by `user_id`, timestamp, and `order_id`. Every order except the final order can produce one sample. Its history includes the complete anchor order and all earlier orders; its target is the immediately following order's `final_order_category`. Multiple products in one order therefore cannot become separate sequential purchases.

The first electronics order is allowed as history for predicting a second order, so the minimum history is one complete prior order. Users with only one order produce no supervised sample. The validation report separately counts users without a future order and samples removed for insufficient history.

## Features

The model feature columns contain only historical information:

- historical order and purchase counts;
- total, mean, minimum, and maximum previous order spending;
- mean historical item price;
- unique historical product and brand counts;
- days since the previous order and average historical order interval;
- historical category diversity, counts, and proportions;
- latest historical category, most frequent historical category, latest historical brand, and latest historical product;
- historical order counts in 30-day and 90-day windows before the target timestamp.

The target order's category, product, brand, price, timestamp, and order ID are not feature columns. `user_id` is retained as an audit/grouping field but is also excluded from model features.

## Target categories and rare classes

The Phase 1 category mapping is preserved. A provisional next-order dataset is first constructed, then categories with fewer than the default 100 future-target samples are merged into `other_electronics` before the final dataset is rebuilt. This applies the threshold to the quantity that matters for supervised learning: target occurrences. The report includes both raw order counts and raw target counts. In the current audit, gaming has 137 source orders but only 52 future targets, so it is merged into `other_electronics`; camera, desktop, and telephone are retained when their actual target counts meet the threshold. `smartwatch_clocks` is retained as the Phase 1 label.

## Audit columns and leakage validation

The derived dataset contains these validation-only audit columns:

- `history_end_order_id`
- `history_end_timestamp`
- `target_order_id`
- `prediction_timestamp`

They are explicitly excluded from `feature_columns`. `next_purchase_category` is the target and is also excluded. The report checks that history precedes the target timestamp, or uses the order ID tie-break when timestamps are equal, and records explicit booleans for audit-column and target-order exclusion.

The report distinguishes exact duplicate supervised samples, identified using user and history/target audit identity, from repeated feature signatures. Repeated signatures with different users or order identities are legitimate repeated historical states and are not treated as duplicate samples.

## Output files

The manual pipeline writes `ml/data/phase2_training.csv.gz` with supervised samples and audit fields, and `ml/reports/phase2_validation.json` with counts, target distribution, feature names, missing values, duplicates, temporal range, and leakage checks. These are derived artifacts; the original CSV is never overwritten or copied.

## Manual validation command

Run this from the ElectroPredict project root in the normal VS Code Conda terminal:

```powershell
python ml/phase2_pipeline.py
```

Optional reproducibility controls are available with `--chunksize`, `--rare-threshold`, `--output`, and `--report`.

## Limitations

The dataset has no quantity field, so repeated rows are not interpreted as quantity. A multi-category order must be represented by one deterministic primary category. The target is next electronics order category, not exact product demand. Later model training must preserve chronological evaluation and must not use audit columns.

The existing Flask entry point remains `app.py`, with SQLite at `instance/electropredict.db`; Phase 2 does not modify either.

## Phase 3: temporal Random Forest baseline

`model_training.py` loads `ml/data/phase2_training.csv.gz` and predicts `next_purchase_category`. It removes the target, `user_id`, audit columns, and `prediction_timestamp` from the model feature matrix. The timestamp is used only to sort rows before an approximately 80/20 chronological split; no random shuffle is used. The exact train/test counts and timestamp boundary are written to `ml/reports/phase3_validation.json`.

Numerical features use a training-fitted median imputer. `previous_product`, `previous_brand`, `previous_category`, and `most_frequent_previous_category` are explicitly categorical even when pandas reads product identifiers as integers. Other history fields retain their detected numeric types. Categorical history features use a training-fitted frequency cap (`min_frequency=10`) followed by `OneHotEncoder(handle_unknown="ignore")`; unseen test values are therefore safe. A `RandomForestClassifier` uses `class_weight="balanced"`, `random_state=42`, 300 trees, and `min_samples_leaf=2`. This is a practical explainable baseline, not an expensive hyperparameter search.

The script evaluates only the later holdout and writes accuracy, macro F1, weighted F1, per-class precision/recall/F1, a majority-class baseline, and a confusion matrix. It also writes transformed-feature importances, correctly aligned to one-hot feature names. The fitted preprocessing/model pipeline is saved as `ml/artifacts/phase3_random_forest_pipeline.joblib` and immediately reloaded by the script as a serialization check.

Run Phase 3 manually from the project root in the normal VS Code Conda terminal:

```powershell
python -m ml.model_training
```

Outputs are written under `ml/artifacts/` and `ml/reports/`: `phase3_random_forest_pipeline.joblib`, `phase3_validation.json`, `classification_report.csv`, `confusion_matrix.csv`, and `feature_importance.csv`. The model predicts only the next electronics purchase category; it does not predict an exact product or purchase date. Later SHAP and explanation work must load this saved pipeline and must not use the excluded identity/audit fields.

## Phase 4: SHAP explainability

`explainability.py` loads the saved Phase 3 joblib pipeline and one Phase 2 sample. It applies the pipeline's fitted preprocessing, runs `shap.TreeExplainer` on the fitted Random Forest, selects the SHAP vector for the class actually returned by `pipeline.predict`, and records its probability. For multiclass SHAP, it supports both older list-of-arrays output and newer 3D array output. One-hot contributions are mapped to source feature names and retained with their transformed names and actual SHAP values. Positive and negative contributors are ranked separately. No SHAP value is manually constructed.

Run it manually after Phase 3:

```powershell
python -m ml.explainability
```

It writes `ml/reports/phase4_shap_validation.json`. The report contains no user ID or order identifier and records the explained class, class probabilities, SHAP output structure, and actual contributors.

## Phase 5: Gemini explanation

`generative_explanation.py` sends only the existing Random Forest prediction, its probability, and aggregated top positive/negative source-feature contributions from the Phase 4 SHAP report to Google Gemini. The supplied category, probability, feature values, and SHAP values are explicitly identified as authoritative ML/SHAP evidence. Gemini is instructed not to predict, recalculate, change the class, invent feature values, invent SHAP values, expose identity/audit fields, or claim causation. It only produces concise natural language. Missing `GEMINI_API_KEY`, missing `google-genai`, empty responses, and API/network failures return a deterministic evidence-based fallback while preserving the ML prediction.

The backend-only key is read from `GEMINI_API_KEY`; it is never hard-coded or sent to frontend code. A template is provided at `.env.example`. Configure the package and `GEMINI_API_KEY` environment variable in the normal Conda terminal, then run:

```powershell
python -m ml.generative_explanation
```

It writes `ml/reports/phase5_gemini_validation.json`. This phase does not add Flask routes or UI integration.
