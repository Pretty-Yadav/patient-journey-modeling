"""Competing-risk cumulative incidence for readmission and death."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sksurv.nonparametric import cumulative_incidence_competing_risks

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COHORT_PATH = REPOSITORY_ROOT / "data/processed/cohort_phase3.csv"
DEFAULT_OUTPUT_PATH = REPOSITORY_ROOT / "reports/cumulative_incidence.png"
DEFAULT_TIME_POINTS = [30, 90, 180]


def prepare_competing_risk_data(cohort: pd.DataFrame) -> pd.DataFrame:
    """Validate and standardize competing-risk data."""
    required = {"time_to_event_days", "event"}
    missing = required.difference(cohort.columns)
    if missing:
        raise ValueError(
            "cohort is missing required competing-risk columns: "
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
    if not data["event"].isin([0, 1, 2]).all():
        raise ValueError("cohort.event must contain only 0, 1, or 2")

    data["event_code"] = data["event"].astype(int)
    data["readmission_indicator"] = (data["event_code"] == 1).astype(int)
    data["death_indicator"] = (data["event_code"] == 2).astype(int)
    return data[
        [
            "subject_id",
            "time_to_event_days",
            "event",
            "event_code",
            "readmission_indicator",
            "death_indicator",
        ]
    ].copy()


def compute_cumulative_incidence(
    cohort: pd.DataFrame,
    time_points: list[int | float] | tuple[int | float, ...] | None = None,
) -> pd.DataFrame:
    """Compute the Aalen-Johansen cumulative incidence for each competing event."""
    data = prepare_competing_risk_data(cohort)
    event = data["event_code"].to_numpy(dtype=int)
    time = data["time_to_event_days"].to_numpy(dtype=float)

    observed_time_points, cif = cumulative_incidence_competing_risks(event, time)
    if time_points is None:
        time_points = observed_time_points.tolist()
    selected = []
    for target_time in [float(point) for point in time_points]:
        if observed_time_points.size == 0:
            readmission_value = 0.0
            death_value = 0.0
        else:
            index = int(np.searchsorted(observed_time_points, target_time, side="right") - 1)
            if index < 0:
                index = 0
            if index >= observed_time_points.size:
                index = observed_time_points.size - 1
            readmission_value = float(cif[1, index])
            death_value = float(cif[2, index])
        selected.append(
            {"time_point": float(target_time), "event_type": "readmission", "cumulative_incidence": readmission_value}
        )
        selected.append(
            {"time_point": float(target_time), "event_type": "death", "cumulative_incidence": death_value}
        )
    return pd.DataFrame(selected)


def plot_cumulative_incidence(
    cohort: pd.DataFrame,
    output_path: Path,
    time_points: list[int | float] | tuple[int | float, ...] | None = None,
) -> Path:
    """Plot cumulative incidence curves for readmission and death."""
    data = prepare_competing_risk_data(cohort)
    observed_time_points, cif = cumulative_incidence_competing_risks(
        data["event_code"].to_numpy(dtype=int),
        data["time_to_event_days"].to_numpy(dtype=float),
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(10, 6))
    plt.step(
        observed_time_points,
        cif[1, :],
        where="post",
        label="Readmission",
    )
    plt.step(
        observed_time_points,
        cif[2, :],
        where="post",
        label="Death",
    )
    plt.xlabel("Days after index discharge")
    plt.ylabel("Cumulative incidence")
    plt.title("Competing risks: readmission vs death")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Estimate cumulative incidence for readmission and death in a competing-risk setting."
    )
    parser.add_argument(
        "--cohort",
        type=Path,
        default=DEFAULT_COHORT_PATH,
        help="Cohort CSV path with time_to_event_days and event columns.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to save the cumulative incidence plot.",
    )
    parser.add_argument(
        "--time-points",
        nargs="*",
        default=[str(value) for value in DEFAULT_TIME_POINTS],
        help="Time points for printed cumulative incidence estimates.",
    )
    args = parser.parse_args()

    cohort_path = args.cohort
    if not cohort_path.is_absolute():
        cohort_path = REPOSITORY_ROOT / cohort_path
    output_path = args.output
    if not output_path.is_absolute():
        output_path = REPOSITORY_ROOT / output_path

    cohort = pd.read_csv(cohort_path)
    result = compute_cumulative_incidence(cohort, time_points=[float(val) for val in args.time_points])
    print("Competing-risk cumulative incidence")
    print(f"Patients in cohort: {len(cohort)}")
    print(f"Readmission events: {int((cohort['event'] == 1).sum())}")
    print(f"Death events: {int((cohort['event'] == 2).sum())}")
    print("Cumulative incidence by time point:")
    for _, row in result.iterrows():
        print(f"{int(row['time_point'])} days | {row['event_type']}: {row['cumulative_incidence']:.3f}")

    plot_cumulative_incidence(cohort, output_path)
    print(f"Saved cumulative incidence plot to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
