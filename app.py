import math

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# Load the saved model and configuration.
artifact = joblib.load("models/fraud_model.joblib")

model = artifact["model"]
feature_names = artifact["features"]
threshold = artifact["threshold"]

app = FastAPI(
    title="Payment Fraud Detection API",
    description="Score transactions and flag potential fraud for review.",
    version="1.0.0",
)


class Transaction(BaseModel):
    features: dict[str, float]


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": artifact["model_name"],
    }


@app.post("/predict")
def predict(transaction: Transaction):
    expected = set(feature_names)
    received = set(transaction.features)

    # Check that all required features are present.
    if expected != received:
        raise HTTPException(
            status_code=422,
            detail={
                "missing_features": sorted(expected - received),
                "unexpected_features": sorted(received - expected),
            },
        )

    # Reject invalid numerical values.
    if not all(
        math.isfinite(value)
        for value in transaction.features.values()
    ):
        raise HTTPException(
            status_code=422,
            detail="All feature values must be finite numbers.",
        )

    # Arrange features in the same order used during training.
    row = pd.DataFrame(
        [[transaction.features[name] for name in feature_names]],
        columns=feature_names,
    )

    score = float(model.predict_proba(row)[0, 1])

    return {
        "risk_score": score,
        "flagged_for_review": bool(score >= threshold),
        "threshold": threshold,
        "model": artifact["model_name"],
    }