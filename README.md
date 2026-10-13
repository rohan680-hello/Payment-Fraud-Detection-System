# Payment Fraud Detection

A machine-learning project that identifies potentially fraudulent card transactions. It compares two classification models, selects the stronger one using validation data, saves the trained artifact, and exposes predictions through a FastAPI service.

## Project structure

```
data/creditcard.csv        Transaction dataset (not included in source control)
models/fraud_model.joblib  Saved selected model, feature list, and threshold
train.py                   Training, validation, testing, and artifact creation
app.py                     FastAPI prediction service
check_data.py              Basic dataset quality checks
results.json               Latest evaluation results
sample_request.json        Example request body for the API
```

## Setup

Use Python 3.11 or a compatible Python version. From the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install pandas numpy scikit-learn xgboost fastapi "uvicorn[standard]" joblib
```

If PowerShell prevents activation, run the following once for the current shell, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Dataset

This project uses the widely used Credit Card Fraud Detection dataset (`data/creditcard.csv`). Each row represents a card transaction:

- `Time`: seconds elapsed since the first transaction in the dataset.
- `V1` to `V28`: anonymized features produced through PCA.
- `Amount`: transaction value.
- `Class`: target label — `0` for legitimate and `1` for fraud.

The dataset is severely imbalanced: fraudulent transactions are rare. Before training, the script removes exact duplicate rows. You can inspect the dataset shape, labels, and missing values with:

```powershell
python check_data.py
```

## Train the model

Place `creditcard.csv` inside the `data` directory, then run:

```powershell
python train.py
```

The training script:

1. Splits the data into 60% training, 20% validation, and 20% test sets using stratified sampling.
2. Trains Logistic Regression and XGBoost models.
3. Uses validation average precision to select the model.
4. Selects a decision threshold that maximizes validation F1 score.
5. Evaluates the selected model once on the held-out test set.
6. Saves the model artifact to `models/fraud_model.joblib`, metrics to `results.json`, and a valid sample payload to `sample_request.json`.

## Models

### Logistic Regression

The baseline is a `StandardScaler` plus Logistic Regression pipeline. It uses `class_weight="balanced"` to give the minority fraud class more influence during training.

### XGBoost

The gradient-boosted tree model uses `scale_pos_weight`, derived from the training class ratio, to handle class imbalance. It also uses subsampling and column sampling to help generalization.

The model with the higher validation average precision is selected. Average precision is more informative than accuracy for this rare-event problem because it focuses on ranking and precision-recall performance.

## Latest results

The saved run selected **XGBoost**.

| Metric | Result |
| --- | ---: |
| Logistic Regression validation average precision | 0.6923 |
| XGBoost validation average precision | 0.7822 |
| Test average precision | 0.8436 |
| Decision threshold | 0.9589 |
| Fraud precision (test) | 0.8621 |
| Fraud recall (test) | 0.7895 |
| Fraud F1 score (test) | 0.8242 |

Test-set confusion matrix at this threshold:

| Actual / Predicted | Legitimate | Fraud |
| --- | ---: | ---: |
| Legitimate | 56,639 | 12 |
| Fraud | 20 | 75 |

These metrics are saved in `results.json`. Results can change if you change the dataset, parameters, or random seed.

## Run the API

Train the model first, then start the server:

```powershell
uvicorn app:app --reload
```

Open the interactive API documentation at <http://127.0.0.1:8000/docs>.

### Endpoints

- `GET /health` confirms that the service and saved model are available.
- `POST /predict` returns a fraud risk score and review decision.

`/predict` expects exactly the model features: `Time`, `V1` through `V28`, and `Amount`. All values must be finite numbers. Missing or unexpected fields return HTTP `422`.

Example request:

```json
{
  "features": {
    "Time": 0.0,
    "V1": -1.36,
    "...": "include V2 through V28",
    "Amount": 149.62
  }
}
```

Use the complete payload from `sample_request.json`; do not send the abbreviated example above.

Example response:

```json
{
  "risk_score": 0.00144,
  "flagged_for_review": false,
  "threshold": 0.95893,
  "model": "XGBoost"
}
```

## Limitations

- The source data is historical and may not reflect current fraud patterns. Fraud behaviour changes over time, so the model requires periodic retraining and monitoring.
- PCA-anonymized features limit interpretability; the API supplies a risk score, not a human-readable fraud reason.
- The F1-optimized threshold is a technical default. A real business should choose it using the cost of false positives, false negatives, and manual review capacity.
- The dataset split is random rather than time-based. A time-based evaluation would better simulate production performance and detect data drift.
- The model is not calibrated or monitored after deployment. Production use should include probability calibration checks, drift monitoring, logging, access controls, and alerting.
- A fraud flag should trigger review, not automatically decline a payment, unless it has been validated within the relevant payment workflow and compliance requirements.

## Next improvements

- Add `requirements.txt` and automated API/model tests.
- Evaluate time-based splits and threshold-cost trade-offs.
- Add model versioning, structured request logging, and monitoring.
- Containerize and deploy the API after adding authentication and rate limiting.
