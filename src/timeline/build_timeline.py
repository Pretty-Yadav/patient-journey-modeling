import pandas as pd
from pathlib import Path


# ---------------------------------------
# File paths
# ---------------------------------------

ADMISSIONS_PATH = Path(
    "physionet.org/files/mimic-iv-demo/2.2/hosp/admissions.csv.gz"
)

COHORT_PATH = Path(
    "data/processed/cohort.csv"
)

OUTPUT_PATH = Path(
    "data/processed/patient_timeline.csv"
)


# ---------------------------------------
# Load data
# ---------------------------------------

print("Loading admissions data...")

admissions = pd.read_csv(
    ADMISSIONS_PATH,
    compression="gzip"
)

cohort = pd.read_csv(
    COHORT_PATH
)


# ---------------------------------------
# Convert dates
# ---------------------------------------

admissions["admittime"] = pd.to_datetime(
    admissions["admittime"]
)

admissions["dischtime"] = pd.to_datetime(
    admissions["dischtime"]
)

cohort["index_admittime"] = pd.to_datetime(
    cohort["index_admittime"]
)

cohort["index_dischtime"] = pd.to_datetime(
    cohort["index_dischtime"]
)


# ---------------------------------------
# Keep only cohort patients
# ---------------------------------------

cohort_patients = cohort["subject_id"].unique()

admissions = admissions[
    admissions["subject_id"].isin(cohort_patients)
].copy()


# ---------------------------------------
# Sort patient admissions
# ---------------------------------------

admissions = admissions.sort_values(
    ["subject_id", "admittime"]
)


# ---------------------------------------
# Build timeline
# ---------------------------------------

timeline_rows = []


for subject_id, patient_admissions in admissions.groupby("subject_id"):

    patient_admissions = patient_admissions.sort_values(
        "admittime"
    )

    for _, admission in patient_admissions.iterrows():

        timeline_rows.append({
            "subject_id": subject_id,
            "hadm_id": admission["hadm_id"],
            "event_type": "hospital_admission",
            "event_time": admission["admittime"],
            "admission_type": admission["admission_type"],
            "discharge_location": admission["discharge_location"]
        })

        timeline_rows.append({
            "subject_id": subject_id,
            "hadm_id": admission["hadm_id"],
            "event_type": "hospital_discharge",
            "event_time": admission["dischtime"],
            "admission_type": admission["admission_type"],
            "discharge_location": admission["discharge_location"]
        })


# ---------------------------------------
# Create DataFrame
# ---------------------------------------

timeline = pd.DataFrame(timeline_rows)


# ---------------------------------------
# Sort timeline
# ---------------------------------------

timeline = timeline.sort_values(
    ["subject_id", "event_time"]
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
print("PATIENT TIMELINE CREATED")
print("=" * 60)

print(f"Patients: {timeline['subject_id'].nunique()}")
print(f"Timeline events: {len(timeline)}")

print("\nEvent types:")
print(timeline["event_type"].value_counts())

print("\nFirst 10 timeline events:")
print(timeline.head(10).to_string(index=False))

print("\nSaved to:")
print(OUTPUT_PATH)

print("=" * 60)
