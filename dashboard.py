import json
import os
from pathlib import Path
import requests
import streamlit as st

# Configure Streamlit page layout and appearance
st.set_page_config(
    page_title="Payment Fraud Detection Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
        background: linear-gradient(90deg, #1E3A8A, #3B82F6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #6B7280;
        margin-bottom: 1.5rem;
    }
    .status-card {
        padding: 1.25rem;
        border-radius: 0.75rem;
        margin-bottom: 1rem;
        border: 1px solid #E5E7EB;
    }
    .status-flagged {
        background-color: #FEF2F2;
        border-color: #F87171;
        color: #991B1B;
    }
    .status-approved {
        background-color: #F0FDF4;
        border-color: #4ADE80;
        color: #166534;
    }
    .metric-container {
        display: flex;
        gap: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Read backend URL from environment variable, falling back to localhost
DEFAULT_API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")

# Sidebar configuration
st.sidebar.header("⚙️ Backend Service")
api_url_input = st.sidebar.text_input(
    "FastAPI Base URL",
    value=DEFAULT_API_URL,
    help="Configured via API_URL environment variable. Can be adjusted for testing.",
)
api_url = api_url_input.strip().rstrip("/")

# Backend Health Check utility
def check_backend_health(url: str):
    health_endpoint = f"{url}/health"
    try:
        response = requests.get(health_endpoint, timeout=6)
        if response.status_code == 200:
            data = response.json()
            return True, data.get("model", "Unknown"), "Service is healthy and responding."
        return False, None, f"Service returned HTTP {response.status_code}: {response.text}"
    except requests.exceptions.ConnectionError:
        return False, None, "Connection refused. Ensure the FastAPI backend is running and the URL is correct."
    except requests.exceptions.Timeout:
        return False, None, "Connection timed out. (Render free tier services may take 30-60s to wake up)."
    except Exception as exc:
        return False, None, f"Error: {exc}"

if st.sidebar.button("Test Backend Connection", use_container_width=True):
    with st.sidebar:
        with st.spinner("Connecting to backend..."):
            is_ok, model_name, message = check_backend_health(api_url)
            if is_ok:
                st.success(f"Online: {message}")
                st.info(f"Loaded Model: **{model_name}**")
            else:
                st.error(f"Offline: {message}")

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    ### 📌 About
    This dashboard evaluates card transactions for potential payment fraud.
    
    - **Model**: Trained machine-learning classifier (e.g. XGBoost)
    - **Inputs**: 30 numerical features (`Time`, `V1`–`V28`, `Amount`)
    - **Decision**: Flags transactions when risk score meets or exceeds the calibrated threshold.
    """
)

# Header Section
st.markdown('<div class="main-header">🛡️ Payment Fraud Detection</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Interactive transaction risk evaluation connected to FastAPI backend.</div>',
    unsafe_allow_html=True,
)

# Preset loader function
def load_sample_file():
    sample_path = Path("sample_request.json")
    if sample_path.exists():
        try:
            with open(sample_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Failed to read sample_request.json: {e}")
    return None

# Manage Session State for input data
if "transaction_data" not in st.session_state:
    sample_data = load_sample_file()
    if sample_data:
        st.session_state["transaction_data"] = sample_data
    else:
        st.session_state["transaction_data"] = {"features": {}}

# Input Selection Tabs
col_input, col_results = st.columns([1, 1], gap="large")

with col_input:
    st.subheader("1. Transaction Input")
    input_method = st.radio(
        "Choose transaction data source:",
        options=["Load sample_request.json", "Upload JSON File", "Direct JSON Editor"],
        horizontal=True,
    )

    if input_method == "Load sample_request.json":
        if st.button("Reload sample_request.json", type="secondary"):
            loaded = load_sample_file()
            if loaded:
                st.session_state["transaction_data"] = loaded
                st.success("Loaded sample_request.json successfully!")
            else:
                st.warning("sample_request.json not found on disk.")

    elif input_method == "Upload JSON File":
        uploaded_file = st.file_uploader(
            "Upload a transaction JSON file",
            type=["json"],
            help="File must contain a 'features' dictionary with Time, V1-V28, and Amount.",
        )
        if uploaded_file is not None:
            try:
                uploaded_content = json.load(uploaded_file)
                st.session_state["transaction_data"] = uploaded_content
                st.success(f"Uploaded and parsed `{uploaded_file.name}` successfully!")
            except json.JSONDecodeError as err:
                st.error(f"Invalid JSON file format: {err}")
            except Exception as exc:
                st.error(f"Error reading file: {exc}")

    # Editable JSON payload area
    st.markdown("##### Payload Preview & Editor")
    current_json_str = json.dumps(st.session_state["transaction_data"], indent=2)
    user_edited_json = st.text_area(
        "Edit or inspect JSON request body:",
        value=current_json_str,
        height=320,
        help="JSON must match {'features': {'Time': ..., 'V1': ..., ..., 'Amount': ...}}",
    )

    # Validate JSON string locally
    parsed_payload = None
    json_is_valid = False
    try:
        parsed_payload = json.loads(user_edited_json)
        if not isinstance(parsed_payload, dict):
            st.error("JSON payload must be a JSON object (dictionary).")
        elif "features" not in parsed_payload:
            st.warning("⚠️ Payload is missing top-level `'features'` key.")
        elif not isinstance(parsed_payload["features"], dict):
            st.error("`'features'` must be a dictionary of feature names and values.")
        else:
            json_is_valid = True
            st.session_state["transaction_data"] = parsed_payload
    except json.JSONDecodeError as err:
        st.error(f"JSON Syntax Error: {err}")

    # Feature inspection preview
    if json_is_valid and isinstance(parsed_payload, dict) and "features" in parsed_payload:
        feats = parsed_payload["features"]
        feat_count = len(feats)
        if feat_count == 30:
            st.caption(f"✅ Found all 30 required features. Amount: **${feats.get('Amount', 0.0):.2f}**, Time: **{feats.get('Time', 0.0)}s**")
        else:
            st.caption(f"⚠️ Payload contains {feat_count} features (30 expected: Time, V1–V28, Amount).")

    predict_btn = st.button("🚀 Run Fraud Prediction", type="primary", use_container_width=True)

with col_results:
    st.subheader("2. Prediction & Risk Assessment")

    if predict_btn:
        if not json_is_valid or parsed_payload is None:
            st.error("Cannot send request: Please fix invalid JSON input.")
        else:
            endpoint = f"{api_url}/predict"
            with st.spinner("Calling fraud scoring API..."):
                try:
                    response = requests.post(
                        endpoint,
                        json=parsed_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=10,
                    )

                    if response.status_code == 200:
                        result = response.json()
                        risk_score = float(result.get("risk_score", 0.0))
                        flagged = bool(result.get("flagged_for_review", False))
                        threshold = float(result.get("threshold", 0.5))
                        model_name = str(result.get("model", "N/A"))

                        # Display High-Level Decision Banner
                        if flagged:
                            st.markdown(
                                f"""
                                <div class="status-card status-flagged">
                                    <h3 style="margin:0 0 0.5rem 0;">🚨 FLAGGED FOR MANUAL REVIEW</h3>
                                    <p style="margin:0;">High fraud risk detected! The calculated risk score <b>({risk_score:.4f})</b> meets or exceeds the operational threshold <b>({threshold:.4f})</b>.</p>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                f"""
                                <div class="status-card status-approved">
                                    <h3 style="margin:0 0 0.5rem 0;">✅ TRANSACTION APPROVED</h3>
                                    <p style="margin:0;">Transaction appears legitimate. The risk score <b>({risk_score:.4f})</b> is below the fraud threshold <b>({threshold:.4f})</b>.</p>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                        # Metric Cards
                        m1, m2, m3 = st.columns(3)
                        with m1:
                            st.metric(
                                label="Risk Score",
                                value=f"{risk_score:.4f}",
                                delta=f"{(risk_score - threshold):.4f} vs threshold" if flagged else f"{(risk_score - threshold):.4f} vs threshold",
                                delta_color="inverse" if flagged else "normal",
                            )
                        with m2:
                            st.metric(
                                label="Review Decision",
                                value="FLAGGED" if flagged else "APPROVED",
                            )
                        with m3:
                            st.metric(
                                label="Active Model",
                                value=model_name,
                            )

                        # Visual Risk Meter
                        st.markdown("##### Risk Gauge")
                        clamped_score = min(max(risk_score, 0.0), 1.0)
                        st.progress(clamped_score)
                        st.caption(f"Score: **{risk_score:.2%}** | Decision Threshold: **{threshold:.2%}**")

                        # Detailed metrics summary
                        with st.expander("Detailed Scoring Parameters", expanded=True):
                            st.write(
                                {
                                    "model_name": model_name,
                                    "risk_score": risk_score,
                                    "decision_threshold": threshold,
                                    "flagged_for_review": flagged,
                                    "verdict": "Manual Review Required" if flagged else "Auto-Approve",
                                }
                            )

                        with st.expander("Raw API JSON Response"):
                            st.json(result)

                    elif response.status_code == 422:
                        st.error("Validation Error (HTTP 422): Invalid input data.")
                        error_details = response.json().get("detail", {})
                        if isinstance(error_details, dict):
                            missing = error_details.get("missing_features", [])
                            unexpected = error_details.get("unexpected_features", [])
                            if missing:
                                st.warning(f"**Missing Features ({len(missing)}):** `{', '.join(missing)}`")
                            if unexpected:
                                st.warning(f"**Unexpected Features ({len(unexpected)}):** `{', '.join(unexpected)}`")
                        else:
                            st.warning(str(error_details))
                        with st.expander("Response Body"):
                            st.json(response.json())

                    else:
                        st.error(f"API Error (HTTP {response.status_code}): {response.text}")

                except requests.exceptions.ConnectionError:
                    st.error(
                        f"🚨 **Backend Unavailable:** Could not connect to `{api_url}`.\n\n"
                        "- Verify that the FastAPI backend is running.\n"
                        "- If running locally, start it with `uvicorn app:app --port 8000`.\n"
                        "- If running on Render, check if the service is spinning up or sleeping."
                    )
                except requests.exceptions.Timeout:
                    st.error(
                        "⏱️ **Backend Request Timed Out:** The backend took longer than 10 seconds to respond.\n\n"
                        "- Render free instances sleep after inactivity and take 30-60 seconds to boot up on initial request.\n"
                        "- Please wait a moment and retry."
                    )
                except Exception as exc:
                    st.error(f"Unexpected error when communicating with backend: {exc}")
    else:
        st.info("👈 Load or upload transaction JSON on the left, then click **Run Fraud Prediction**.")
