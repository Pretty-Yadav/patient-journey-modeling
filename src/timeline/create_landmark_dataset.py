
from pathlib import Path
import pandas as pd

COHORT_PATH = Path("data/processed/cohort.csv")
TIMELINE_PATH = Path("data/processed/patient_journey_180d.csv")
OUTPUT_PATH = Path("data/processed/landmark_dataset.csv")

LANDMARK_DAY = 30
FOLLOWUP_DAY = 180


def main():
    cohort = pd.read_csv(COHORT_PATH)
    timeline = pd.read_csv(TIMELINE_PATH)

    cohort["time_to_event_days"] = pd.to_numeric(
        cohort["time_to_event_days"], errors="coerce"
    )
    timeline["days_from_index"] = pd.to_numeric(
        timeline["days_from_index"], errors="coerce"
    )

    # Keep patients whose first recorded outcome is after Day 30.
    eligible = cohort[
        cohort["time_to_event_days"] > LANDMARK_DAY
    ].copy()

    # Only use journey events recorded during Days 0-30.
    early = timeline[
        timeline["subject_id"].isin(eligible["subject_id"])
        & (timeline["days_from_index"] >= 0)
        & (timeline["days_from_index"] <= LANDMARK_DAY)
    ].copy()

    # Count each type of early journey event.
    counts = (
        early.pivot_table(
            index="subject_id",
            columns="event_type",
            values="days_from_index",
            aggfunc="count",
            fill_value=0,
        )
        .add_prefix("events_")
        .reset_index()
    )

    diagnosis_counts = (
        early[early["event_type"] == "diagnosis"]
        .groupby("subject_id")
        .size()
        .rename("diagnosis_count_day30")
        .reset_index()
    )

    distinct_diagnoses = (
        early[early["event_type"] == "diagnosis"]
        .groupby("subject_id")["event_description"]
        .nunique()
        .rename("distinct_diagnoses_day30")
        .reset_index()
    )

    landmark = eligible[
        [
            "subject_id",
            "gender",
            "anchor_age",
            "event_label",
            "time_to_event_days",
        ]
    ].copy()

    landmark = landmark.merge(counts, on="subject_id", how="left")
    landmark = landmark.merge(
        diagnosis_counts, on="subject_id", how="left"
    )
    landmark = landmark.merge(
        distinct_diagnoses, on="subject_id", how="left"
    )

    feature_columns = [
        c for c in landmark.columns if c.startswith("events_")
    ] + ["diagnosis_count_day30", "distinct_diagnoses_day30"]

    landmark[feature_columns] = landmark[feature_columns].fillna(0)

    # 0 = censored, 1 = readmission, 2 = death.
    landmark["outcome_code"] = landmark["event_label"].map(
        {"censored": 0, "readmission": 1, "death": 2}
    )

    landmark["time_after_landmark_days"] = (
        landmark["time_to_event_days"] - LANDMARK_DAY
    ).clip(lower=0, upper=FOLLOWUP_DAY - LANDMARK_DAY)

    landmark["readmission_after_day30"] = (
        landmark["event_label"] == "readmission"
    ).astype(int)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    landmark.to_csv(OUTPUT_PATH, index=False)

    print("DAY 30 LANDMARK DATASET CREATED")
    print("Patients:", landmark["subject_id"].nunique())
    print("Dataset shape:", landmark.shape)
    print("\nOutcome counts:")
    print(landmark["event_label"].value_counts().to_string())
    print("\nSaved to:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
