# Cohort definition: prototype

## Target population

The prototype identifies patients with at least one hospital admission carrying
an ICD code whose local diagnosis-dictionary title contains “heart failure”
and does not contain “without heart failure.” This preserves the repository's
existing code-based inclusion approach while correcting the index-admission
selection. It is a title-search heuristic, not a clinically validated code
set; the resulting population should not be described as a validated heart
failure cohort.

## Inclusion and index admission

- A patient must have a diagnosis row linked by both `subject_id` and `hadm_id`
  to an admission, and that diagnosis code/version must match a selected
  heart-failure dictionary entry.
- The index is that patient's earliest admission with a qualifying
  heart-failure diagnosis. An earlier admission without such a diagnosis is
  not the index.
- One row per `subject_id` is retained.
- Admissions with `hospital_expire_flag == 1` are excluded because the
  time origin is discharge and these patients did not enter post-discharge
  follow-up. A recorded date of death on or before the index discharge date is
  also excluded conservatively because date-only death data cannot establish
  survival after discharge on the same calendar day.

The prototype does not currently apply additional age, admission-type, primary
diagnosis, or clinical exclusion criteria. It requires review before use as a
research cohort.

## Time origin, outcomes, and follow-up

- **Time origin:** the index admission's `dischtime`.
- **Readmission (event 1):** first subsequent admission in the supplied
  admissions table with `admittime > index_dischtime`. This is an all-cause
  readmission to the represented hospital, not specifically a heart-failure
  readmission and not a claim about admissions to other hospitals.
- **Death (event 2):** the recorded patient death date after index discharge.
  Death and readmission are competing first events.
- **Censoring (event 0):** the earliest of the explicitly provided
  administrative complete-through date and the 180-day follow-up horizon, if
  no event occurs first.
- A date-only administrative end is interpreted inclusively through the end
  of that calendar day. The date must be supported by documented source
  completeness; it must not be inferred from a patient's last event or
  selected merely to obtain 180 days of follow-up.
- MIMIC's `dod` is date-level while readmission is timestamped. If both events
  occur on the same calendar day, exact ordering is unknown; death is assigned
  as the conservative tie-break. Event-time precision on that day remains
  limited by the date-only death field.

The administrative cutoff represents a study-level ascertainment assumption
for this hospital dataset. The source must actually be complete through that
date for outcomes of interest. The code cannot establish completeness,
out-of-hospital readmission capture, or continuous patient observation from
the date alone.

## Flow counts

The cohort builder returns and prints aggregate counts for patients in the
patient table, patients with a qualifying diagnosis, eligible index admissions,
index-discharge death exclusions, final cohort size, and each first-event
category. It does not print patient identifiers.

## Reproduction

After the required local source files have passed validation, run from the
repository root using a complete-through date established from source
provenance. For the current local demo extract, the last observed discharge in
`admissions.csv.gz` is 2201-12-17, so an administrative end date of that day is
consistent with the available hospital data in this workspace:

```bash
python -m src.cohort.build_cohort \
  --data-dir physionet.org/files/mimic-iv-demo/2.2/hosp \
  --administrative-end-date 2201-12-17 \
  --output data/processed/cohort_phase3.csv \
  --overwrite
```

The builder refuses to replace an existing output unless `--overwrite` is
explicitly supplied. In a real study, do not use a date copied from an
example; choose the administrative date from verified source documentation.

## Limitations

The current local MIMIC-IV Demo extract includes `patients.csv.gz`, and the
cohort builder can run against it with a documented administrative end date.
The code's diagnosis-title heuristic, the all-cause admission readmission
definition, and the assumption of complete readmission ascertainment within the
available hospital records still require research review. The MIMIC-IV Demo
sample is small and is intended to exercise methods and code, not establish
clinical performance or population estimates.
