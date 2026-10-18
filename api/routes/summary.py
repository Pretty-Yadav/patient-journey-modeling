from __future__ import annotations

from pathlib import Path

import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
COHORT_PATH = REPOSITORY_ROOT / "data/processed/cohort_phase3.csv"
FALLBACK_COHORT_PATH = REPOSITORY_ROOT / "data/processed/cohort.csv"
PREDICTIONS_PATH = REPOSITORY_ROOT / "data/processed/xgboost_predictions.csv"
FEATURE_IMPORTANCE_PATH = REPOSITORY_ROOT / "reports/xgboost_feature_importance.csv"
SUBGROUP_PATH = REPOSITORY_ROOT / "reports/subgroup_analysis.csv"


def _safe_read_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


def get_summary() -> dict:
    cohort = _safe_read_csv(COHORT_PATH)
    if cohort is None:
        cohort = _safe_read_csv(FALLBACK_COHORT_PATH)
    predictions = _safe_read_csv(PREDICTIONS_PATH)
    feature_importance = _safe_read_csv(FEATURE_IMPORTANCE_PATH)
    subgroup = _safe_read_csv(SUBGROUP_PATH)

    prediction_records = []
    if predictions is not None:
        records = predictions.copy()
        records.insert(0, "record_number", range(1, len(records) + 1))
        if "gender" in records:
            records["gender"] = records["gender"].map({0: "Male", 1: "Female"}).fillna("Unknown")
        prediction_records = records.to_dict(orient="records")

    summary: dict[str, object] = {
        "status": "ok",
        "cohort": {
            "rows": int(len(cohort)) if cohort is not None else 0,
            "readmission_events": int((cohort["event"] == 1).sum()) if cohort is not None else 0,
            "death_events": int((cohort["event"] == 2).sum()) if cohort is not None else 0,
            "censored": int((cohort["event"] == 0).sum()) if cohort is not None else 0,
        },
        "model": {
            "patients": int(len(predictions)) if predictions is not None else 0,
            "positive_label_rate": float(predictions["readmission_180d"].mean()) if predictions is not None else 0.0,
            "mean_predicted_probability": float(predictions["predicted_probability"].mean()) if predictions is not None else 0.0,
        },
        "predictions": prediction_records,
        "feature_importance": (
            feature_importance.to_dict(orient="records") if feature_importance is not None else []
        ),
        "subgroup_analysis": (
            subgroup.to_dict(orient="records") if subgroup is not None else []
        ),
    }
    return summary
