# Data source, provenance, and handling

## Source and access

The repository's local directory structure identifies the available extract as MIMIC-IV Demo version 2.2, under `physionet.org/files/mimic-iv-demo/2.2/hosp/`. This is local-path evidence only: the repository does not contain a source download manifest, checksums, acquisition date, or proof of the source files' provenance. Record those details when the authorized source package is obtained.

MIMIC-IV data are governed by PhysioNet access and data-use requirements. Obtain and use data only under the applicable current PhysioNet credentialing and data-use agreement. Do not publish raw data or patient-level derived records. This repository does not verify a user's authorization or the license status of files placed in the workspace.

## Local input inventory

The cohort builder requires these compressed CSVs:

| File | Role | Current local status |
|---|---|---|
| `patients.csv.gz` | Patient demographics and date of death used by cohort construction | Present; gzip readable and required schema columns found |
| `admissions.csv.gz` | Admission and discharge dates, admission identifiers | Present; gzip readable and required schema columns found |
| `diagnoses_icd.csv.gz` | Admission diagnoses and ICD codes | Present; gzip readable and required schema columns found |
| `d_icd_diagnoses.csv.gz` | ICD code descriptions | Present; gzip readable and required schema columns found |

The current local source audit found 100 patients, 275 admissions, 4,506 diagnosis rows, and 109,775 diagnosis-dictionary rows. These are row counts in the local files, not evidence of complete follow-up or population coverage. Aggregate schema and quality checks are recorded in [`../reports/data_quality_report.md`](../reports/data_quality_report.md).

## Reproducing input validation

From the repository root, run:

```bash
python -m src.data.validate_inputs
```

For a local copy in another location:

```bash
python -m src.data.validate_inputs --data-dir /path/to/mimic-iv-demo/2.2/hosp
```

The validator checks input presence, gzip/CSV readability, required columns, non-empty files, primary-key duplicates, identifier missingness, parseable admission dates, discharge-before-admission inconsistencies, and available cross-table references. It emits aggregate diagnostics only and does not change source files. A nonzero exit status means one or more required checks failed. Unit tests use small synthetic tables and do not require access to MIMIC data.

The validator is a prototype quality gate, not a complete clinical or research validation. It does not verify a source checksum, enforce every upstream MIMIC-IV constraint, establish an observation end date, or determine whether a row is clinically valid.

## Storage and privacy

Raw PhysioNet files under `physionet.org/` and generated files under `data/processed/` are ignored by Git. Ignore rules do not remove files already tracked: several derived files, including the cohort and baseline predictions, are already tracked in this repository. Review their contents and applicable data-use terms before distribution. No files were untracked or deleted as part of this audit.

Do not put patient identifiers, row-level extracts, secrets, or unredacted logs into reports or screenshots. Prefer aggregate validation findings. Keep raw files local, access-controlled, and separate from versioned source code. Do not treat de-identification or date shifting as permission to redistribute MIMIC data.

## Current limitations

The local MIMIC-IV Demo source in this workspace includes `patients.csv.gz`, and the validator reports the required hospital tables as present and readable. Patient-specific follow-up end dates must still be established from source-supported administrative data before the cohort can be treated as fully validated for follow-up and outcome ascertainment. The current prototype should not be interpreted as a clinically validated population estimate.

The Phase 3 prototype defines one row per patient, selects the earliest
heart-failure-coded admission as index, counts any subsequent admission in the
available hospital table as all-cause readmission, and requires an explicit
administrative complete-through date. The date must be justified from the
source; it must not be inferred from the last observed patient event. See
[`cohort_definition.md`](cohort_definition.md) for rules and limitations.

Phase 4 provides a canonical hospital/diagnosis event table and a bounded
first-event journey. Diagnosis records are assigned their admission time as an
encounter proxy, not interpreted as onset. The bounded journey stops at the
first readmission or death, or at the explicit follow-up end. See
[`states_and_timeline.md`](states_and_timeline.md). The legacy cohort does not
contain `followup_end_date`, and the patient source table remains unavailable,
so do not treat existing timeline outputs as regenerated or validated.