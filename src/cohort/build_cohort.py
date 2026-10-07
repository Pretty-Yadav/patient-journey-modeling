from pathlib import Path
import pandas as pd


# ============================================================
# 1. FILE PATHS
# ============================================================

DATA_DIR = Path("physionet.org/files/mimic-iv-demo/2.2/hosp")

OUTPUT_PATH = Path("data/processed/cohort.csv")

MAX_FOLLOWUP_DAYS = 180


# ============================================================
# 2. LOAD MIMIC-IV DATA
# ============================================================

print("Loading data...")

patients = pd.read_csv(
    DATA_DIR / "patients.csv.gz"
)

admissions = pd.read_csv(
    DATA_DIR / "admissions.csv.gz"
)

diagnoses = pd.read_csv(
    DATA_DIR / "diagnoses_icd.csv.gz"
)

diagnosis_dictionary = pd.read_csv(
    DATA_DIR / "d_icd_diagnoses.csv.gz"
)

print("Data loaded successfully.")


# ============================================================
# 3. FIND HEART FAILURE DIAGNOSIS CODES
# ============================================================

heart_failure_codes = diagnosis_dictionary[
    diagnosis_dictionary["long_title"].str.contains(
        "heart failure",
        case=False,
        na=False
    )
    &
    ~diagnosis_dictionary["long_title"].str.contains(
        "without heart failure",
        case=False,
        na=False
    )
][
    ["icd_code", "icd_version"]
]

print(
    f"Heart failure diagnosis codes found: "
    f"{len(heart_failure_codes)}"
)


# ============================================================
# 4. FIND HEART FAILURE PATIENTS
# ============================================================

hf_diagnoses = diagnoses.merge(
    heart_failure_codes,
    on=["icd_code", "icd_version"],
    how="inner"
)

hf_patients = hf_diagnoses["subject_id"].unique()

print(
    f"Heart failure patients found: "
    f"{len(hf_patients)}"
)


# ============================================================
# 5. KEEP ADMISSIONS OF HEART FAILURE PATIENTS
# ============================================================

admissions["admittime"] = pd.to_datetime(
    admissions["admittime"]
)

admissions["dischtime"] = pd.to_datetime(
    admissions["dischtime"]
)

hf_admissions = admissions[
    admissions["subject_id"].isin(hf_patients)
].copy()


# ============================================================
# 6. SORT ADMISSIONS
# ============================================================

hf_admissions = hf_admissions.sort_values(
    ["subject_id", "admittime"]
)


# ============================================================
# 7. DEFINE INDEX ADMISSION
# ============================================================

index_admissions = (
    hf_admissions
    .groupby("subject_id", as_index=False)
    .first()
)

index_admissions = index_admissions[
    [
        "subject_id",
        "hadm_id",
        "admittime",
        "dischtime"
    ]
].rename(
    columns={
        "hadm_id": "index_hadm_id",
        "admittime": "index_admittime",
        "dischtime": "index_dischtime"
    }
)


# ============================================================
# 8. ADD PATIENT INFORMATION
# ============================================================

cohort = index_admissions.merge(
    patients[
        [
            "subject_id",
            "gender",
            "anchor_age",
            "dod"
        ]
    ],
    on="subject_id",
    how="left"
)

cohort["dod"] = pd.to_datetime(
    cohort["dod"]
)


# ============================================================
# 9. FIND SUBSEQUENT ADMISSIONS
# ============================================================

subsequent_admissions = hf_admissions.merge(
    index_admissions[
        [
            "subject_id",
            "index_dischtime"
        ]
    ],
    on="subject_id",
    how="inner"
)

subsequent_admissions = subsequent_admissions[
    subsequent_admissions["admittime"]
    > subsequent_admissions["index_dischtime"]
].copy()


# ============================================================
# 10. FIND FIRST READMISSION
# ============================================================

first_readmission = (
    subsequent_admissions
    .groupby("subject_id", as_index=False)["admittime"]
    .min()
    .rename(
        columns={
            "admittime": "readmission_date"
        }
    )
)

cohort = cohort.merge(
    first_readmission,
    on="subject_id",
    how="left"
)


# ============================================================
# 11. DETERMINE FIRST EVENT
# ============================================================

# Event definitions:
#
# 0 = Censored
# 1 = Readmission
# 2 = Death

cohort["event"] = 0

cohort["event_date"] = pd.NaT


for idx, row in cohort.iterrows():

    index_discharge = row["index_dischtime"]

    readmission_date = row["readmission_date"]

    death_date = row["dod"]

    # Maximum follow-up = 180 days
    followup_end = (
        index_discharge
        + pd.Timedelta(days=MAX_FOLLOWUP_DAYS)
    )

    possible_events = []

    # Check readmission
    if pd.notna(readmission_date):

        if readmission_date <= followup_end:

            possible_events.append(
                (readmission_date, 1)
            )

    # Check death
    if pd.notna(death_date):

        if (
            death_date >= index_discharge
            and death_date <= followup_end
        ):

            possible_events.append(
                (death_date, 2)
            )

    # Select the earliest event
    if possible_events:

        possible_events.sort(
            key=lambda x: x[0]
        )

        first_date, first_event = possible_events[0]

        cohort.loc[
            idx,
            "event"
        ] = first_event

        cohort.loc[
            idx,
            "event_date"
        ] = first_date


# ============================================================
# 12. CALCULATE TIME TO EVENT
# ============================================================

cohort["time_to_event_days"] = (
    cohort["event_date"]
    - cohort["index_dischtime"]
).dt.total_seconds() / (
    60 * 60 * 24
)


# ============================================================
# 13. CENSOR PATIENTS WITHOUT AN EVENT
# ============================================================

cohort["time_to_event_days"] = (
    cohort["time_to_event_days"]
    .fillna(MAX_FOLLOWUP_DAYS)
)


# ============================================================
# 14. CREATE READABLE EVENT LABEL
# ============================================================

cohort["event_label"] = cohort["event"].map(
    {
        0: "censored",
        1: "readmission",
        2: "death"
    }
)


# ============================================================
# 15. SAVE COHORT
# ============================================================

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)

cohort.to_csv(
    OUTPUT_PATH,
    index=False
)


# ============================================================
# 16. PRINT RESULTS
# ============================================================

print()
print("========================================")
print("COHORT CREATED SUCCESSFULLY")
print("========================================")

print(
    f"Number of patients: {len(cohort)}"
)

print()
print("Event distribution:")

print(
    cohort["event_label"]
    .value_counts()
)

print()
print("First 10 patients:")

print(
    cohort[
        [
            "subject_id",
            "index_hadm_id",
            "index_admittime",
            "index_dischtime",
            "gender",
            "anchor_age",
            "event",
            "event_label",
            "time_to_event_days"
        ]
    ]
    .head(10)
    .to_string(index=False)
)

print()
print("Cohort saved to:")

print(OUTPUT_PATH)