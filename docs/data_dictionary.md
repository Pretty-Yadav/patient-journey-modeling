# Data dictionary

This dictionary describes the columns required by the current ingestion and
validation prototype. It is not a full MIMIC-IV dictionary. Source table
definitions and permitted uses must be checked against the applicable
MIMIC-IV documentation and data-use agreement.

## `patients.csv.gz`

| Column | Expected role | Validation |
|---|---|---|
| `subject_id` | Patient identifier used to link patient-level records | Required; checked for missing values and duplicate keys |
| `gender` | Recorded gender category | Required column; categories are not normalized by this validator |
| `anchor_age` | Age field supplied by the de-identified dataset | Required; nonmissing values must be numeric |
| `dod` | Date of death, when recorded | Required column; missing values are allowed; nonmissing values must parse as dates |

## `admissions.csv.gz`

| Column | Expected role | Validation |
|---|---|---|
| `subject_id` | Patient identifier | Required; checked for missing values and patient-table references when that table is available |
| `hadm_id` | Hospital admission identifier | Required; checked for duplicates |
| `admittime` | Admission timestamp | Required; must parse as a date/time |
| `dischtime` | Discharge timestamp | Required; must parse as a date/time and not precede admission |
| `hospital_expire_flag` | Indicates death during the admission | Required by cohort builder; used to exclude patients who do not enter post-discharge follow-up |

The timeline scripts also use additional admissions columns, including
`admission_type` and `discharge_location`. The current validator checks
`hospital_expire_flag` is present but does not validate its values; the cohort
builder requires values to be 0 or 1.

## `diagnoses_icd.csv.gz`

| Column | Expected role | Validation |
|---|---|---|
| `subject_id` | Patient identifier | Required |
| `hadm_id` | Admission identifier | Required; subject/admission pairs checked against admissions |
| `seq_num` | Diagnosis sequence within an admission | Required; part of duplicate-key check |
| `icd_code` | Diagnosis code | Required |
| `icd_version` | ICD coding-system version | Required; paired with code for dictionary linkage |

## `d_icd_diagnoses.csv.gz`

| Column | Expected role | Validation |
|---|---|---|
| `icd_code` | Diagnosis code | Required; part of duplicate-key check |
| `icd_version` | ICD coding-system version | Required; paired with code for dictionary linkage |
| `long_title` | Text description of the diagnosis code | Required and nonmissing |

## Derived cohort fields

The currently tracked `data/processed/cohort.csv` includes `subject_id`,
`index_hadm_id`, `index_admittime`, `index_dischtime`, `gender`, `anchor_age`,
`dod`, `readmission_date`, `event`, `event_date`, `time_to_event_days`, and
`event_label`. These describe the existing artifact only. In particular, its
`time_to_event_days` value of 180 for rows without a recorded event does not
establish 180 days of observed follow-up. Do not use those rows as confirmed
180-day event-free observations until censoring is derived from verified
patient-specific observation information.

The updated cohort builder adds `followup_end_date` and
`administrative_end_date`. It requires an explicit complete-through date, then
sets censor duration to the earlier of that date and 180 days after index
discharge when no event occurs. An administrative date is only valid when
source provenance supports complete observation through it.

The event timeline and bounded-journey schemas are documented in
[`states_and_timeline.md`](states_and_timeline.md).
