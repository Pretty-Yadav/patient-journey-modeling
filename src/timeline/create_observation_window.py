import pandas as pd
from pathlib import Path


# ---------------------------------------
# File paths
# ---------------------------------------

TIMELINE_PATH = Path(
    "data/processed/patient_enriched_timeline.csv"
)

COHORT_PATH = Path(
    "data/processed/cohort.csv"
)

OUTPUT_PATH = Path(
    "data/processed/patient_journey_180d.csv"
)


# ---------------------------------------
# Load data
# ---------------------------------------

timeline = pd.read_csv(
    TIMELINE_PATH,
    parse_dates=["event_time"]
)

cohort = pd.read_csv(
    COHORT_PATH,
    parse_dates=[
        "index_admittime",
        "index_dischtime",
        "event_date"
    ]
)


# ---------------------------------------
# Merge index admission information
# ---------------------------------------

timeline = timeline.merge(
    cohort[
        [
            "subject_id",
            "index_hadm_id",
            "index_admittime",
            "index_dischtime",
            "event",
            "event_date"
        ]
    ],
    on="subject_id",
    how="inner"
)


# ---------------------------------------
# Define observation window
# ---------------------------------------

timeline["window_start"] = timeline["index_dischtime"]

timeline["window_end"] = (
    timeline["index_dischtime"]
    + pd.Timedelta(days=180)
)


# ---------------------------------------
# Keep events within 180 days
# ---------------------------------------

timeline = timeline[
    (timeline["event_time"] >= timeline["window_start"])
    & (timeline["event_time"] <= timeline["window_end"])
].copy()


# ---------------------------------------
# Calculate time from index discharge
# ---------------------------------------

timeline["days_from_index"] = (
    timeline["event_time"]
    - timeline["index_dischtime"]
).dt.total_seconds() / (24 * 60 * 60)


timeline["days_from_index"] = (
    timeline["days_from_index"].round(2)
)


# ---------------------------------------
# Sort events
# ---------------------------------------

timeline = timeline.sort_values(
    [
        "subject_id",
        "event_time",
        "event_type"
    ]
).reset_index(drop=True)


# ---------------------------------------
# Save
# ---------------------------------------

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)

timeline.to_csv(
    OUTPUT_PATH,
    index=False
)


# ---------------------------------------
# Summary
# ---------------------------------------

print("=" * 60)
print("180-DAY PATIENT JOURNEY CREATED")
print("=" * 60)

print(f"Patients: {timeline['subject_id'].nunique()}")
print(f"Timeline events: {len(timeline)}")

print("\nEvent types:")
print(
    timeline["event_type"].value_counts()
)

print("\nDays from index:")
print(
    timeline["days_from_index"].describe()
)

print("\nFirst 15 events:")
print(
    timeline[
        [
            "subject_id",
            "hadm_id",
            "event_type",
            "event_time",
            "days_from_index",
            "event_description"
        ]
    ].head(15).to_string(index=False)
)

print("\nSaved to:")
print(OUTPUT_PATH)

print("=" * 60)
