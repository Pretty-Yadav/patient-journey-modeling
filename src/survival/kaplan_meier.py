"""Kaplan-Meier survival analysis for first-event outcomes."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from lifelines import KaplanMeierFitter

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COHORT_PATH = REPOSITORY_ROOT / "data/processed/cohort_phase3.csv"
DEFAULT_OUTPUT_PATH = REPOSITORY_ROOT / "reports/kaplan_meier_overall.png"
DEFAULT_TIME_POINTS = [30, 90, 180]


def prepare_survival_data(cohort: pd.DataFrame) -> pd.DataFrame:
    """Return a validated dataset with a binary any-event indicator.

    The Kaplan-Meier estimand here is the probability of remaining event-free
    up to time t, where the event is any first observed outcome (readmission or
    death). This is not the same as the cumulative incidence of readmission in
    the presence of competing death.
    """
    required = {"time_to_event_days", "event"}
    missing = required.difference(cohort.columns)
    if missing:
        raise ValueError(
            "cohort is missing required survival columns: "
            f"{sorted(missing)}"
        )

    data = cohort.copy()
    data["time_to_event_days"] = pd.to_numeric(
        data["time_to_event_days"], errors="raise"
    )
    data["event"] = pd.to_numeric(data["event"], errors="raise")
    if data["time_to_event_days"].isna().any():
        raise ValueError("cohort contains missing time_to_event_days values")
    if (data["time_to_event_days"] < 0).any():
        raise ValueError("time_to_event_days cannot be negative")

    data["overall_event"] = (
        data["event"].fillna(0).astype(int).gt(0)
    ).astype(int)
    return data[["subject_id", "time_to_event_days", "event", "overall_event"]].copy()


def fit_kaplan_meier(cohort: pd.DataFrame) -> KaplanMeierFitter:
    """Fit a Kaplan-Meier model for "any first event"."""
    data = prepare_survival_data(cohort)
    kmf = KaplanMeierFitter()
    kmf.fit(
        durations=data["time_to_event_days"],
        event_observed=data["overall_event"],
        label="Any first event",
    )
    return kmf


def estimate_survival_probability(
    kmf: KaplanMeierFitter,
    time_points: list[int | float] | tuple[int | float, ...] | None = None,
) -> pd.Series:
    """Return survival estimates at selected time points."""
    if time_points is None:
        time_points = DEFAULT_TIME_POINTS
    values = [float(point) for point in time_points]
    probabilities = [kmf.predict(point) for point in values]
    return pd.Series(probabilities, index=values, name="survival_probability")


def plot_kaplan_meier(
    kmf: KaplanMeierFitter,
    output_path: Path,
    time_horizon: int | float | None = 180,
) -> Path:
    """Create and save the Kaplan-Meier curve."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(10, 6))
    kmf.plot_survival_function()
    plt.title("Kaplan-Meier curve: time to any first event")
    plt.xlabel("Days after index discharge")
    plt.ylabel("Probability of remaining event-free")
    if time_horizon is not None:
        plt.xlim(0, time_horizon)
    plt.ylim(0, 1.05)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fit a Kaplan-Meier estimator for time to any first readmission or death "
            "after index discharge."
        )
    )
    parser.add_argument(
        "--cohort",
        type=Path,
        default=DEFAULT_COHORT_PATH,
        help="Cohort CSV with time_to_event_days and event columns.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to save the Kaplan-Meier plot PNG.",
    )
    parser.add_argument(
        "--time-points",
        nargs="*",
        default=[str(value) for value in DEFAULT_TIME_POINTS],
        help="Time points for printed survival probabilities, e.g. 30 90 180",
    )
    args = parser.parse_args()

    cohort_path = args.cohort
    if not cohort_path.is_absolute():
        cohort_path = REPOSITORY_ROOT / cohort_path
    output_path = args.output
    if not output_path.is_absolute():
        output_path = REPOSITORY_ROOT / output_path

    cohort = pd.read_csv(cohort_path)
    kmf = fit_kaplan_meier(cohort)
    time_points = [float(point) for point in args.time_points]
    predictions = estimate_survival_probability(kmf, time_points)

    print("Kaplan-Meier analysis: any first event")
    print(f"Patients in cohort: {len(cohort)}")
    print(f"Any-event count: {cohort['event'].fillna(0).astype(int).gt(0).sum()}")
    print(f"Censored count: {cohort['event'].fillna(0).astype(int).eq(0).sum()}")
    print("Survival probabilities at requested time points:")
    for time_value, probability in predictions.items():
        print(f"{int(time_value)} days: {probability:.3f}")

    plot_kaplan_meier(kmf, output_path, time_horizon=180)
    print(f"Saved Kaplan-Meier curve to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
