# Deployment Guide: Payment Fraud Detection on Render

This guide explains how to deploy the Payment Fraud Detection system on [Render](https://render.com). The project consists of two components:
1. **FastAPI Backend (`app.py`)**: REST API for fraud scoring and model health checks.
2. **Streamlit Frontend Dashboard (`dashboard.py`)**: Interactive web UI allowing users to load `sample_request.json`, upload custom transaction JSON files, inspect features, and view real-time risk scores and review decisions.

---

## Architecture Overview

```
+-----------------------------------+          HTTP POST /predict          +-----------------------------------+
|      Streamlit Dashboard          | -----------------------------------> |        FastAPI Backend            |
|        (dashboard.py)             |                                      |           (app.py)                |
|  Reads: $API_URL                  | <----------------------------------- |  Loads: models/fraud_model.joblib |
|  Uploads / sample_request.json    |          JSON Risk Score & Decision  |  XGBoost Classifier + Threshold   |
+-----------------------------------+                                      +-----------------------------------+
```

---

## Pre-Deployment Checklist

### 1. Model Artifact Availability in Git
Render builds services by cloning your Git repository. Ensure `models/fraud_model.joblib` is tracked and committed:

```bash
# Check git status to confirm the model file is tracked
git status -u models/
```

The repository `.gitignore` has been pre-configured to allow the model artifact:
```gitignore
models/*
!models/fraud_model.joblib
```

To add and commit the model:
```bash
git add models/fraud_model.joblib
git add .gitignore requirements.txt dashboard.py app.py render.yaml
git commit -m "Prepare services, dashboard, and dependencies for Render deployment"
git push origin main
```

### 2. Dependency Versions
The model artifact was trained using:
- `scikit-learn==1.9.1`
- `xgboost==3.2.0`
- `pandas==3.0.6`
- `numpy==2.4.6`
- `scipy==1.17.1`
- `joblib==1.6.0`

These exact versions are pinned in `requirements.txt` to prevent serialization and unpickling mismatches during deployment.

---

## Option A: One-Click Deploy via Render Blueprint (Recommended)

The repository includes a ready-to-use `render.yaml` blueprint that deploys and links both services automatically.

1. Push your repository to GitHub or GitLab.
2. Log into the [Render Dashboard](https://dashboard.render.com).
3. Click **New +** and select **Blueprint**.
4. Connect your Git repository.
5. Render will automatically detect `render.yaml` and configure:
   - `payment-fraud-api` (FastAPI backend service)
   - `payment-fraud-dashboard` (Streamlit web service)
   - The `API_URL` environment variable linking dashboard to API
6. Click **Apply**. Both services will build and deploy automatically.

---

## Option B: Manual Service Creation on Render

If you prefer to configure the services manually in the Render dashboard:

### Step 1: Deploy the FastAPI Backend Service

1. On the Render Dashboard, click **New +** > **Web Service**.
2. Connect your Git repository.
3. Configure the service settings:
   - **Name**: `payment-fraud-api`
   - **Region**: Any (e.g., Oregon or Frankfurt)
   - **Branch**: `main`
   - **Runtime**: `Python`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     uvicorn app:app --host 0.0.0.0 --port $PORT
     ```
   - **Health Check Path**: `/health`
4. In **Environment Variables**, add:
   - `PYTHON_VERSION`: `3.11.9`
5. Click **Deploy Web Service**.
6. Once deployed, copy your backend URL (e.g. `https://payment-fraud-api.onrender.com`).

---

### Step 2: Deploy the Streamlit Dashboard Service

1. Click **New +** > **Web Service**.
2. Connect the same Git repository.
3. Configure the service settings:
   - **Name**: `payment-fraud-dashboard`
   - **Region**: Same region as the backend
   - **Branch**: `main`
   - **Runtime**: `Python`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     streamlit run dashboard.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
     ```
4. In **Environment Variables**, add:
   - `PYTHON_VERSION`: `3.11.9`
   - `API_URL`: `https://payment-fraud-api.onrender.com` *(Replace with your actual backend URL from Step 1)*
5. Click **Deploy Web Service**.

---

## Local Development & Testing

You can test both services on your local machine before deploying:

### 1. Activate Environment and Install Requirements
```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Run Automated Local Tests
We provide automated test suites covering endpoint contracts, validation errors, and live HTTP servers:

```powershell
# Unit & integration endpoint tests
python test_services.py

# Live server HTTP integration test
python test_live_services.py

# Streamlit live startup verification
python test_live_dashboard.py
```

### 3. Start the Backend API
```powershell
uvicorn app:app --reload --port 8000
```
- Interactive API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health Check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 4. Start the Streamlit Dashboard (In a second terminal)
```powershell
.\.venv\Scripts\Activate.ps1
streamlit run dashboard.py
```
- Open [http://localhost:8501](http://localhost:8501) in your browser.
- By default, the dashboard connects to `http://127.0.0.1:8000`. You can also override it using the `$env:API_URL` environment variable or the sidebar input.

---

## Troubleshooting & Render Specifics

- **Render Free Tier Spin-Down**:
  On Render's free plan, web services spin down after 15 minutes of inactivity. The first request may take 30–60 seconds to wake up. The Streamlit dashboard includes built-in timeout handling and connection test tools to explain this to the user.
- **Model File Not Found**:
  If the API logs show `FileNotFoundError: Model artifact not found at .../models/fraud_model.joblib`, confirm that `models/fraud_model.joblib` was not ignored by `.gitignore` and has been pushed to your remote repository.
- **CORS Issues**:
  The FastAPI service has been configured with `CORSMiddleware` (`allow_origins=["*"]`), ensuring API requests succeed across origins.
