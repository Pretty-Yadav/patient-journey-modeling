"""Cause-specific Cox model for readmission or death as the event of interest."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from lifelines import CoxPHFitter

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COHORT_PATH = REPOSITORY_ROOT / "data/processed/cohort_phase3.csv"


def prepare_cause_specific_data(
    cohort: pd.DataFrame,
    event_of_interest: int = 1,
) -> pd.DataFrame:
    """Prepare a cause-specific hazard dataset with readmission or death as target event."""
    required = {"time_to_event_days", "event", "anchor_age", "gender"}
    missing = required.difference(cohort.columns)
    if missing:
        raise ValueError(
            "cohort is missing required cause-specific model columns: "
            f"{sorted(missing)}"
        )

    data = cohort.copy()
    data["time_to_event_days"] = pd.to_numeric(
        data["time_to_event_days"], errors="raise"
    )
    data["event"] = pd.to_numeric(data["event"], errors="raise")
    data["anchor_age"] = pd.to_numeric(data["anchor_age"], errors="raise")
    data["gender"] = data["gender"].map({"M": 0, "F": 1})
    if data["gender"].isna().any():
        raise ValueError("gender must be encoded as M or F")

    if event_of_interest not in {1, 2}:
        raise ValueError("event_of_interest must be 1 (readmission) or 2 (death)")

    model_df = data[
        ["time_to_event_days", "event", "anchor_age", "gender"]
    ].copy()
    model_df["target_event"] = (model_df["event"] == event_of_interest).astype(int)
    model_df = model_df.dropna().copy()
    if model_df.empty:
        raise ValueError("No rows available after dropping missing values")
    if model_df["target_event"].sum() < 3:
        print(
            "Warning: very few events are available for the cause-specific model; "
            "hazard ratios may be unstable."
        )
    return model_df[["time_to_event_days", "target_event", "anchor_age", "gender"]].copy()


def fit_cause_specific_cox(
    cohort: pd.DataFrame,
    event_of_interest: int = 1,
) -> CoxPHFitter:
    """Fit a cause-specific Cox model for a single event type."""
    model_df = prepare_cause_specific_data(cohort, event_of_interest=event_of_interest)
    cph = CoxPHFitter()
    cph.fit(
        model_df,
        duration_col="time_to_event_days",
        event_col="target_event",
    )
    return cph


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fit a cause-specific Cox model for readmission or death with other events treated as censoring."
    )
    parser.add_argument(
        "--cohort",
        type=Path,
        default=DEFAULT_COHORT_PATH,
        help="Cohort CSV with time_to_event_days, event, anchor_age and gender.",
    )
    parser.add_argument(
        "--event-type",
        choices=["readmission", "death"],
        default="readmission",
        help="Which event to model as the target event.",
    )
    args = parser.parse_args()

    cohort_path = args.cohort
    if not cohort_path.is_absolute():
        cohort_path = REPOSITORY_ROOT / cohort_path

    cohort = pd.read_csv(cohort_path)
    event_map = {"readmission": 1, "death": 2}
    cph = fit_cause_specific_cox(cohort, event_of_interest=event_map[args.event_type])
    print(f"Cause-specific Cox model: {args.event_type}")
    print(f"Rows used: {len(cph.summary)}")
    print(cph.summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
