from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    precision_recall_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


# Load data and remove exact duplicate rows.
df = pd.read_csv("data/creditcard.csv").drop_duplicates()

X = df.drop(columns="Class")
y = df["Class"]

# Split: 60% training, 20% validation, 20% testing.
X_train, X_remaining, y_train, y_remaining = train_test_split(
    X, y,
    test_size=0.4,
    stratify=y,
    random_state=42,
)

X_val, X_test, y_val, y_test = train_test_split(
    X_remaining, y_remaining,
    test_size=0.5,
    stratify=y_remaining,
    random_state=42,
)

print("Training rows:", len(X_train))
print("Validation rows:", len(X_val))
print("Testing rows:", len(X_test))

# Give fraud cases more importance during training.
fraud_weight = (y_train == 0).sum() / (y_train == 1).sum()

models = {
    "Logistic Regression": Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(
            class_weight="balanced",
            max_iter=2000,
            random_state=42,
        )),
    ]),
    "XGBoost": XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=float(fraud_weight),
        eval_metric="logloss",
        tree_method="hist",
        random_state=42,
        n_jobs=2,
    ),
}

best_model = None
best_name = None
best_ap = -1.0
validation_results = {}

# Select the model using validation data only.
for name, model in models.items():
    print(f"\nTraining {name}...", flush=True)
    model.fit(X_train, y_train)

    scores = model.predict_proba(X_val)[:, 1]
    ap = float(average_precision_score(y_val, scores))
    validation_results[name] = ap

    print(f"Validation average precision: {ap:.4f}")

    if ap > best_ap:
        best_ap = ap
        best_model = model
        best_name = name

# Select a threshold that maximizes validation F1.
val_scores = best_model.predict_proba(X_val)[:, 1]

precision, recall, thresholds = precision_recall_curve(
    y_val, val_scores
)

f1_scores = (
    2 * precision[:-1] * recall[:-1]
    / (precision[:-1] + recall[:-1] + 1e-12)
)

threshold = float(thresholds[np.argmax(f1_scores)])

# Evaluate the selected model on the test set.
test_scores = best_model.predict_proba(X_test)[:, 1]
predictions = (test_scores >= threshold).astype(int)

test_ap = float(average_precision_score(y_test, test_scores))
report = classification_report(
    y_test, predictions,
    output_dict=True,
    zero_division=0,
)
matrix = confusion_matrix(y_test, predictions)

print("\nSelected model:", best_name)
print(f"Selected threshold: {threshold:.4f}")
print(f"Test average precision: {test_ap:.4f}")
print("\nClassification report:")
print(classification_report(
    y_test, predictions,
    digits=4,
    zero_division=0,
))
print("Confusion matrix:")
print(matrix)

# Save the model, preprocessing and threshold together.
Path("models").mkdir(exist_ok=True)

joblib.dump({
    "model": best_model,
    "features": X.columns.tolist(),
    "threshold": threshold,
    "model_name": best_name,
}, "models/fraud_model.joblib")

# Save results for your README.
results = {
    "validation_average_precision": validation_results,
    "selected_model": best_name,
    "threshold": threshold,
    "test_average_precision": test_ap,
    "classification_report": report,
    "confusion_matrix": matrix.tolist(),
}

Path("results.json").write_text(
    json.dumps(results, indent=2),
    encoding="utf-8",
)

# Save an example transaction for testing the API later.
sample = {
    "features": {
        column: float(value)
        for column, value in X_test.iloc[0].items()
    }
}

Path("sample_request.json").write_text(
    json.dumps(sample, indent=2),
    encoding="utf-8",
)

print("\nSaved model, results.json and sample_request.json")