import numpy as np
import streamlit as st
from inference import THRESHOLD, classify, load_bundle, predict

st.set_page_config(page_title="ICU Mortality Prediction", page_icon="🩺", layout="wide")
st.title("ICU Mortality Prediction with MIMIC-III")
st.caption("Portfolio demonstration of a mortality risk prediction model using the first 24 hours of ICU data.")
st.warning("This application is a portfolio and research demonstration only. It is not a medical device and must not be used for diagnosis, treatment, triage, or clinical decision-making.")


@st.cache_resource
def artifacts():
    return load_bundle()


try:
    bundle = artifacts()
except (OSError, ValueError, KeyError) as exc:
    st.error(f"Unable to load the model artifact bundle: {exc}")
    st.info("Restore the committed models/ bundle and install requirements.txt before running the app.")
    st.stop()

schema, manifest = bundle[2:]
with st.sidebar:
    st.header("Research demo")
    st.metric("Fixed classification threshold", "0.60")
    st.write("First 24 hours · Adult ICU stays · In-hospital mortality")
    st.link_button("View GitHub repository", "https://github.com/sengulozaydin/icu-risk-prediction")
    st.caption("Use fictional inputs. No patient records are bundled or saved by this app.")

GROUPS = ["Demographics", "Laboratory Results", "Vital Signs", "Outputs", "Interventions"]
VITALS = ["Diastolic BP", "GCS Total", "Heart Rate", "Mean BP", "Respiratory Rate", "SpO2", "Systolic BP", "Temperature"]


def group(name):
    if name in schema["categorical_features"] or name == "age":
        return "Demographics"
    if name in ["urine_output_24h", "chest_tube_present", "ebl_present", "ebl_24h"]:
        return "Outputs"
    if name in ["mechanical_ventilation_present", "vasopressor_present", "rrt_present"]:
        return "Interventions"
    if name == "vital_missing" or any(name.startswith(v + "_") for v in VITALS):
        return "Vital Signs"
    return "Laboratory Results"


st.subheader("Enter first-day clinical features")
st.write("Leave unavailable numeric measurements blank: the saved training median imputer handles them. Laboratory change means last minus first; negative changes are valid. Vital statistics refer to the same 24-hour window.")
st.caption("Enter values in the original MIMIC feature units; temperature is °C, blood pressure is mmHg, SpO₂ is %, and outputs are mL. No unit conversion is performed. Age above 89 is represented as 90. Missingness flags describe absence of the entire feature group, not a single test.")
values = {}
with st.form("clinical_inputs"):
    for tab, name in zip(st.tabs(GROUPS), GROUPS):
        with tab:
            if name == "Laboratory Results":
                st.caption("19 laboratory tests: first value and change. Use each test's original MIMIC unit.")
            columns = st.columns(3)
            features = [f for f in schema["features"] if group(f) == name]
            for i, feature in enumerate(features):
                label = feature.replace("_", " ")
                with columns[i % 3]:
                    if feature in schema["categorical_features"]:
                        values[feature] = st.selectbox(label, schema["categories"][feature], key=feature)
                    elif feature in schema["binary_features"]:
                        values[feature] = st.selectbox(label, [0, 1], index=1 if feature in ["lab_missing", "vital_missing"] else 0,
                            format_func=lambda x: "Yes (1)" if x else "No (0)", key=feature,
                            help="Use 1 when present/true, 0 when absent/false.")
                    else:
                        value = st.number_input(label, value=None, format="%.3f", key=feature,
                                                placeholder="Missing — training median")
                        values[feature] = np.nan if value is None else value
    submitted = st.form_submit_button("Predict Mortality Risk", type="primary", use_container_width=True)

if submitted:
    try:
        probability = predict(values, bundle)
        st.subheader("Model output")
        st.metric("Estimated mortality probability", f"{probability:.1%}")
        st.progress(probability)
        st.write(f"Model classification: **{classify(probability)}**")
        st.caption(f"Fixed threshold: {THRESHOLD:.1f}. This is a model score, not a validated individual clinical risk estimate.")
    except (ValueError, TypeError) as exc:
        st.error(f"Check the entered values: {exc}")

with st.expander("About the model"):
    st.write("MIMIC-III · 45,253 adult ICU stays · first 24-hour clinical window · 83 predictors · patient-grouped train/test split.")
    st.write("Final model: Deep Learning, 64 → 32 → 1, ReLU hidden layers and sigmoid output. Threshold: 0.6.")
    st.write("Numeric preprocessing: training median imputation and StandardScaler. Categorical preprocessing: One-Hot Encoding with unknown categories ignored.")
    st.markdown("**Final held-out test metrics recorded in the original notebook**")
    for column, (metric, score) in zip(st.columns(4), manifest["recorded_notebook_test_metrics"].items()):
        column.metric(metric, f"{score:.3f}")
    st.caption(manifest["provenance"])
