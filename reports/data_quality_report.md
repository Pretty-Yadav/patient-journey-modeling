# Data quality report

**Scope:** Read-only audit of files available in the workspace on 2026-10-09.
No source or processed datasets were modified to create this report.

## Input file audit

| File | Status | Rows | Findings |
|---|---:|---:|---|
| `patients.csv.gz` | Present/readable | 100 | Gzip and CSV header are readable; required demographic and death-date columns are present |
| `admissions.csv.gz` | Present/readable | 275 | Gzip and CSV header are readable; required admission identifier and timestamp columns are present |
| `diagnoses_icd.csv.gz` | Present/readable | 4,506 | Gzip and CSV header are readable; required diagnosis and linkage columns are present |
| `d_icd_diagnoses.csv.gz` | Present/readable | 109,775 | Gzip and CSV header are readable; required code and description columns are present |

The source files were inspected for headers and aggregate row/missing-cell
counts. Patient-level rows and identifiers are intentionally not reproduced.
The local file path identifies the extract as MIMIC-IV Demo 2.2, and the
validator confirms the four required hospital tables are present and readable.
Source checksums and acquisition provenance are still not recorded in the
repository, so the provenance trail remains partial.

## Existing processed artifact

The current cohort CSV contains 24 rows. Its outcome codes comprise 17
`censored`, 6 `readmission`, and 1 `death` labels. Each censored row has a
duration of 180 days and no event date; no patient-specific observation-end date
was present to support that duration. These are not validated observations of
180 event-free days.

## Git and data-handling observations

- Raw files under `physionet.org/` are ignored by Git.
- `data/processed/` is ignored for new files, but some previously generated
  processed artifacts are tracked already. Ignore rules do not untrack them.
- The cohort and baseline datasets contain patient/admission identifiers or
  potentially linkable derived fields. Review data-use terms and repository
  access before distributing the repository or derived files.
- No patient-level values are included in this report.

## Recheck

From the repository root run:

```bash
python -m src.data.validate_inputs
```

The validator should report the four required files as `OK` in the current
workspace and exit successfully. It does not download data or write outputs.
See [`../docs/data_plan.md`](../docs/data_plan.md) for scope and limitations.
