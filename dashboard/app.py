from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from api.routes.summary import get_summary

st.set_page_config(page_title="Patient Journey Dashboard", layout="wide")


@st.cache_data(show_spinner=False)
def load_summary() -> dict:
    summary = get_summary()
    if not isinstance(summary, dict):
        raise ValueError("The summary loader returned an invalid response.")
    return summary


try:
    summary = load_summary()
except (OSError, ValueError) as error:
    st.error(f"Could not load dashboard artifacts: {error}")
    st.caption("Check that the processed CSV files and reports are available, then reload.")
    st.stop()

if summary.get("status") != "ok":
    st.error("The dashboard could not load the summary data.")
    st.stop()

cohort = summary["cohort"]
model = summary["model"]
predictions = pd.DataFrame(summary.get("predictions", []))
feature_importance = pd.DataFrame(summary.get("feature_importance", []))
subgroup = pd.DataFrame(summary.get("subgroup_analysis", []))

st.title("Patient Journey Modeling")
st.caption("Cohort outcomes, held-out prediction records, and model evaluation")
st.warning("Research prototype using a small demo cohort. Not for clinical decision-making.", icon="⚠️")

overview_tab, predictions_tab, evaluation_tab = st.tabs(
    ["Overview", "Prediction records", "Model validation"]
)

with overview_tab:
    metric_columns = st.columns(5)
    metric_columns[0].metric("Cohort", f'{cohort["rows"]:,}')
    metric_columns[1].metric("Readmissions", f'{cohort["readmission_events"]:,}')
    metric_columns[2].metric("Deaths", f'{cohort["death_events"]:,}')
    metric_columns[3].metric("Censored", f'{cohort["censored"]:,}')
    metric_columns[4].metric("Prediction records", f'{model["patients"]:,}')

    left, right = st.columns(2)
    with left:
        st.subheader("Cohort outcomes")
        outcome_counts = pd.DataFrame(
            {
                "Patients": [
                    cohort["readmission_events"],
                    cohort["death_events"],
                    cohort["censored"],
                ]
            },
            index=["Readmission", "Death", "Censored"],
        )
        st.bar_chart(outcome_counts, color="#087e8b")
    with right:
        st.subheader("Predicted-risk distribution")
        if not predictions.empty and "predicted_probability" in predictions:
            risk_bins = pd.cut(
                predictions["predicted_probability"],
                bins=[0, 0.2, 0.4, 0.6, 0.8, 1.000001],
                labels=["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"],
                include_lowest=True,
            )
            risk_counts = risk_bins.value_counts(sort=False).rename("Records").to_frame()
            st.bar_chart(risk_counts, color="#f28f3b")
        else:
            st.info("No prediction records are available.")

    st.metric("Observed readmission rate in prediction set", f'{model["positive_label_rate"]:.1%}')

with predictions_tab:
    st.subheader("Held-out prediction records")
    if predictions.empty:
        st.info("No prediction artifact is available yet.")
    else:
        filter_columns = st.columns([1, 1, 2])
        available_genders = sorted(predictions["gender"].dropna().unique().tolist())
        selected_genders = filter_columns[0].multiselect(
            "Gender", available_genders, default=available_genders
        )
        selected_class = filter_columns[1].selectbox(
            "Observed outcome", ["All", "Readmission", "No readmission"]
        )
        risk_threshold = filter_columns[2].slider(
            "Highlight predicted risk at or above", min_value=0, max_value=100, value=50
        ) / 100

        filtered = predictions[predictions["gender"].isin(selected_genders)].copy()
        if selected_class == "Readmission":
            filtered = filtered[filtered["readmission_180d"] == 1]
        elif selected_class == "No readmission":
            filtered = filtered[filtered["readmission_180d"] == 0]

        at_or_above = int((filtered["predicted_probability"] >= risk_threshold).sum())
        st.caption(
            f"{len(filtered)} records shown; {at_or_above} meet the selected risk threshold. "
            "Record numbers are display-only and are not patient identifiers."
        )
        display_columns = [
            "record_number",
            "anchor_age",
            "gender",
            "readmission_180d",
            "predicted_probability",
            "predicted_class",
        ]
        st.dataframe(
            filtered[display_columns],
            hide_index=True,
            width="stretch",
            column_config={
                "record_number": st.column_config.NumberColumn("Record", format="%d"),
                "anchor_age": st.column_config.NumberColumn("Age", format="%d"),
                "readmission_180d": st.column_config.NumberColumn("Observed readmission", format="%d"),
                "predicted_probability": st.column_config.ProgressColumn(
                    "Predicted risk", min_value=0, max_value=1, format="%.1f%%"
                ),
                "predicted_class": st.column_config.NumberColumn("Predicted class", format="%d"),
            },
        )
        st.download_button(
            "Download filtered records",
            data=filtered[display_columns].to_csv(index=False).encode("utf-8"),
            file_name="prediction_records.csv",
            mime="text/csv",
        )

with evaluation_tab:
    st.subheader("Model evaluation")
    evaluation_columns = st.columns(3)
    evaluation_columns[0].metric("Mean predicted risk", f'{model["mean_predicted_probability"]:.1%}')
    evaluation_columns[1].metric("Observed readmission rate", f'{model["positive_label_rate"]:.1%}')
    evaluation_columns[2].metric("Evaluation records", f'{model["patients"]:,}')

    importance_column, subgroup_column = st.columns(2)
    with importance_column:
        st.markdown("#### Feature importance")
        if not feature_importance.empty:
            st.bar_chart(
                feature_importance.sort_values("importance", ascending=True).set_index("feature")[
                    "importance"
                ],
                color="#087e8b",
            )
        else:
            st.info("No feature-importance artifact is available.")
    with subgroup_column:
        st.markdown("#### Subgroup metrics")
        if not subgroup.empty:
            st.dataframe(
                subgroup,
                hide_index=True,
                width="stretch",
                column_config={
                    "brier_score": st.column_config.NumberColumn("Brier score", format="%.4f"),
                    "roc_auc": st.column_config.NumberColumn("ROC-AUC", format="%.4f"),
                },
            )
        else:
            st.info("No subgroup analysis artifact is available.")

    calibration_path = REPOSITORY_ROOT / "reports/xgboost_calibration.png"
    if calibration_path.exists():
        st.markdown("#### Calibration")
        st.image(str(calibration_path), width="stretch")
    st.caption(
        "Metrics are descriptive only. The prediction set is very small; subgroup and overall "
        "performance estimates are unstable and are not evidence of clinical validity."
    )
