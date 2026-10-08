import pandas as pd
from pathlib import Path


# ---------------------------------------
# File paths
# ---------------------------------------

ADMISSIONS_PATH = Path(
    "physionet.org/files/mimic-iv-demo/2.2/hosp/admissions.csv.gz"
)

DIAGNOSES_PATH = Path(
    "physionet.org/files/mimic-iv-demo/2.2/hosp/diagnoses_icd.csv.gz"
)

ICD_DICTIONARY_PATH = Path(
    "physionet.org/files/mimic-iv-demo/2.2/hosp/d_icd_diagnoses.csv.gz"
)

COHORT_PATH = Path(
    "data/processed/cohort.csv"
)

OUTPUT_PATH = Path(
    "data/processed/patient_enriched_timeline.csv"
)


# ---------------------------------------
# Load data
# ---------------------------------------

print("Loading data...")

admissions = pd.read_csv(
    ADMISSIONS_PATH,
    compression="gzip"
)

diagnoses = pd.read_csv(
    DIAGNOSES_PATH,
    compression="gzip"
)

icd_dictionary = pd.read_csv(
    ICD_DICTIONARY_PATH,
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


# ---------------------------------------
# Keep cohort patients
# ---------------------------------------

cohort_patients = cohort["subject_id"].unique()

admissions = admissions[
    admissions["subject_id"].isin(cohort_patients)
].copy()

diagnoses = diagnoses[
    diagnoses["subject_id"].isin(cohort_patients)
].copy()


# ---------------------------------------
# Add diagnosis descriptions
# ---------------------------------------

diagnoses = diagnoses.merge(
    icd_dictionary,
    on=["icd_code", "icd_version"],
    how="left"
)


# ---------------------------------------
# Connect diagnoses to admission dates
# ---------------------------------------

diagnoses = diagnoses.merge(
    admissions[
        [
            "subject_id",
            "hadm_id",
            "admittime",
            "dischtime"
        ]
    ],
    on=["subject_id", "hadm_id"],
    how="inner"
)


# ---------------------------------------
# Build timeline
# ---------------------------------------

timeline_rows = []


# Hospital events
for _, admission in admissions.iterrows():

    timeline_rows.append({
        "subject_id": admission["subject_id"],
        "hadm_id": admission["hadm_id"],
        "event_type": "hospital_admission",
        "event_time": admission["admittime"],
        "event_description": admission["admission_type"]
    })

    timeline_rows.append({
        "subject_id": admission["subject_id"],
        "hadm_id": admission["hadm_id"],
        "event_type": "hospital_discharge",
        "event_time": admission["dischtime"],
        "event_description": admission["discharge_location"]
    })


# Diagnosis events
for _, diagnosis in diagnoses.iterrows():

    timeline_rows.append({
        "subject_id": diagnosis["subject_id"],
        "hadm_id": diagnosis["hadm_id"],
        "event_type": "diagnosis",
        "event_time": diagnosis["admittime"],
        "event_description": diagnosis["long_title"]
    })


# ---------------------------------------
# Create DataFrame
# ---------------------------------------

timeline = pd.DataFrame(timeline_rows)


# ---------------------------------------
# Sort timeline
# ---------------------------------------

timeline = timeline.sort_values(
    ["subject_id", "event_time", "event_type"]
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
print("ENRICHED PATIENT TIMELINE CREATED")
print("=" * 60)

print(f"Patients: {timeline['subject_id'].nunique()}")
print(f"Timeline events: {len(timeline)}")

print("\nEvent types:")
print(
    timeline["event_type"].value_counts()
)

print("\nFirst 15 events:")
print(
    timeline.head(15).to_string(index=False)
)

print("\nSaved to:")
print(OUTPUT_PATH)

print("=" * 60)
