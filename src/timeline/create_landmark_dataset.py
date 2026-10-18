import argparse
from pathlib import Path

import pandas as pd


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
COHORT_PATH = REPOSITORY_ROOT / "data/processed/cohort_phase3.csv"
TIMELINE_PATH = REPOSITORY_ROOT / "data/processed/journey_phase4.csv"
OUTPUT_PATH = REPOSITORY_ROOT / "data/processed/landmark_dataset.csv"

LANDMARK_DAYS = (30, 90)
FOLLOWUP_END_DAY = 180

EVENT_LABELS = {
    1: "readmission",
    2: "death",
}


def _format_censored_label(days_from_index: float) -> str:
    """Return a censored label based on the patient-specific observation end."""
    days_value = float(days_from_index)
    day_count = int(round(days_value))
    return f"no_event_by_day_{day_count}"

HISTORY_EVENT_TYPES = {
    "hospital_admission": "history_hospital_admission_count",
    "hospital_discharge": "history_hospital_discharge_count",
    "diagnosis": "history_diagnosis_count",
}


def create_landmark_dataset(
    cohort: pd.DataFrame,
    timeline: pd.DataFrame,
    landmark_days=LANDMARK_DAYS,
    followup_end_day=FOLLOWUP_END_DAY,
) -> pd.DataFrame:
    """Build event-free landmark rows using history observed by each landmark."""
    cohort_columns = {
        "subject_id",
        "index_hadm_id",
        "index_dischtime",
        "anchor_age",
        "gender",
        "event",
        "event_label",
        "time_to_event_days",
        "followup_end_date",
    }
    timeline_columns = {
        "subject_id",
        "event_type",
        "event_description",
        "days_from_index",
    }
    missing_cohort = cohort_columns.difference(cohort.columns)
    missing_timeline = timeline_columns.difference(timeline.columns)
    if missing_cohort or missing_timeline:
        raise ValueError(
            "Missing required columns: "
            f"cohort={sorted(missing_cohort)}, "
            f"timeline={sorted(missing_timeline)}"
        )

    cohort = cohort.copy()
    timeline = timeline.copy()
    cohort["event"] = cohort["event"].astype(int)
    cohort["index_dischtime"] = pd.to_datetime(
        cohort["index_dischtime"], errors="raise"
    )
    cohort["followup_end_date"] = pd.to_datetime(
        cohort["followup_end_date"], errors="raise"
    )
    cohort["time_to_event_days"] = pd.to_numeric(
        cohort["time_to_event_days"], errors="raise"
    )
    timeline["days_from_index"] = pd.to_numeric(
        timeline["days_from_index"], errors="raise"
    )

    valid_events = set(EVENT_LABELS).union({0})
    unknown_events = set(cohort["event"].unique()).difference(valid_events)
    if unknown_events:
        raise ValueError(f"Unknown cohort event codes: {sorted(unknown_events)}")

    cohort["patient_followup_days"] = (
        cohort["followup_end_date"] - cohort["index_dischtime"]
    ).dt.total_seconds() / 86400
    timeline_end_day = float(cohort["patient_followup_days"].max())
    timeline = timeline[
        timeline["days_from_index"].between(0, timeline_end_day)
    ].copy()
    rows = []

    for landmark_day in landmark_days:
        if followup_end_day is not None and not 0 < landmark_day < followup_end_day:
            raise ValueError(
                "Each landmark day must be after discharge and before "
                "the follow-up end day."
            )

        # Only patients still at risk at the landmark enter this snapshot.
        eligible = cohort[
            (cohort["event"] == 0)
            | (cohort["time_to_event_days"] > landmark_day)
        ].copy()
        if eligible.empty:
            continue

        history = timeline[
            (timeline["days_from_index"] <= landmark_day)
            & timeline["subject_id"].isin(eligible["subject_id"])
        ].copy()

        history_counts = (
            history.groupby(["subject_id", "event_type"])
            .size()
            .unstack(fill_value=0)
        )
        for event_type, column in HISTORY_EVENT_TYPES.items():
            if event_type not in history_counts:
                history_counts[event_type] = 0
            history_counts = history_counts.rename(columns={event_type: column})

        feature_columns = list(HISTORY_EVENT_TYPES.values())
        history_counts = history_counts.reindex(
            columns=feature_columns, fill_value=0
        )
        history_counts["history_event_count"] = history_counts.sum(axis=1)
        unique_diagnoses = (
            history[history["event_type"] == "diagnosis"]
            .groupby("subject_id")["event_description"]
            .nunique()
            .rename("history_unique_diagnosis_count")
        )
        history_counts = history_counts.join(unique_diagnoses, how="left")

        snapshot = eligible.merge(
            history_counts,
            left_on="subject_id",
            right_index=True,
            how="left",
        )
        count_columns = feature_columns + [
            "history_event_count",
            "history_unique_diagnosis_count",
        ]
        snapshot[count_columns] = snapshot[count_columns].fillna(0).astype(int)

        snapshot["landmark_day"] = landmark_day
        snapshot["event_after_landmark"] = snapshot["event"]
        snapshot["patient_followup_days"] = (
            snapshot["followup_end_date"] - snapshot["index_dischtime"]
        ).dt.total_seconds() / 86400
        snapshot["event_after_landmark_label"] = snapshot.apply(
            lambda row: (
                _format_censored_label(row["patient_followup_days"])
                if int(row["event_after_landmark"]) == 0
                else EVENT_LABELS[int(row["event_after_landmark"])]
            ),
            axis=1,
        )
        snapshot["time_to_event_after_landmark_days"] = (
            snapshot["time_to_event_days"] - landmark_day
        )
        snapshot["followup_end_day"] = snapshot["patient_followup_days"]

        rows.append(
            snapshot[
                [
                    "subject_id",
                    "index_hadm_id",
                    "landmark_day",
                    "anchor_age",
                    "gender",
                    *count_columns,
                    "event_after_landmark",
                    "event_after_landmark_label",
                    "time_to_event_after_landmark_days",
                    "followup_end_day",
                ]
            ]
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "subject_id",
                "index_hadm_id",
                "landmark_day",
                "anchor_age",
                "gender",
                *HISTORY_EVENT_TYPES.values(),
                "history_event_count",
                "history_unique_diagnosis_count",
                "event_after_landmark",
                "event_after_landmark_label",
                "time_to_event_after_landmark_days",
                "followup_end_day",
            ]
        )

    return pd.concat(rows, ignore_index=True).sort_values(
        ["subject_id", "landmark_day"]
    ).reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a landmark dataset from the cohort and enriched timeline."
    )
    parser.add_argument(
        "--cohort",
        type=Path,
        default=COHORT_PATH,
        help="Path to the validated cohort CSV.",
    )
    parser.add_argument(
        "--timeline",
        type=Path,
        default=TIMELINE_PATH,
        help="Path to the enriched timeline CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help="Destination CSV for the landmark dataset.",
    )
    args = parser.parse_args()

    cohort_path = args.cohort if args.cohort.is_absolute() else REPOSITORY_ROOT / args.cohort
    timeline_path = args.timeline if args.timeline.is_absolute() else REPOSITORY_ROOT / args.timeline
    output_path = args.output if args.output.is_absolute() else REPOSITORY_ROOT / args.output

    print("Loading cohort and timeline for landmark generation...")
    cohort = pd.read_csv(cohort_path)
    timeline = pd.read_csv(timeline_path)

    dataset = create_landmark_dataset(cohort, timeline)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(output_path, index=False)

    print("=" * 60)
    print("LANDMARK DATASET CREATED")
    print("=" * 60)
    print(f"Rows: {len(dataset)}")
    print(f"Patients: {dataset['subject_id'].nunique()}")
    print(f"Landmarks: {list(LANDMARK_DAYS)} days after index discharge")
    print("\nEligible rows by landmark:")
    print(dataset.groupby("landmark_day").size().to_string())
    print("\nOutcome counts by landmark:")
    print(
        dataset.groupby(
            ["landmark_day", "event_after_landmark_label"]
        ).size().to_string()
    )
    print(f"\nSaved to: {output_path}")
    return 0


if __name__ == "__main__":
    main()