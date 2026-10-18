# Clinical states and timeline schema

## What the available data support

The current source inputs support encounter-level hospital admission and
discharge records, diagnosis codes attached to admissions, and a recorded
patient date of death. They do not establish outpatient encounters, care
transitions outside the represented hospital, symptom onset, medication
exposure timing, or the exact onset time of a diagnosis code.

This prototype therefore represents observed events rather than claiming a
complete clinical state trajectory:

| Event type | Meaning in this prototype | Source and timing |
|---|---|---|
| `hospital_admission` | An admission record for a cohort patient | `admissions.csv.gz.admittime` |
| `hospital_discharge` | A discharge record for that admission | `admissions.csv.gz.dischtime` |
| `diagnosis` | An ICD diagnosis attached to an admission | `diagnoses_icd.csv.gz` joined to the diagnosis dictionary; assigned the admission timestamp as an encounter-time proxy |
| `death` | The cohort's recorded first death event | `patients.csv.gz.dod`, which has date-level precision |

`diagnosis` is an encounter-associated code, not a separate onset or
transition. Its assigned timestamp must not be interpreted as when the
condition began or was clinically recognized. Discharge location and admission
type are retained in source-derived descriptions only when available in the
input fields; they do not by themselves establish a post-discharge care state.

## State interpretation

For a first-event follow-up analysis, the defensible minimal states are:

1. **Post-index-discharge and at risk** — begins at the index discharge.
2. **First readmission** — first later admission in the supplied hospital
   records.
3. **Death** — recorded death before any observed readmission.
4. **Censored** — reaches the verified observation end or 180-day horizon
   without a recorded first event.

Readmission and death are absorbing endpoints for this first-event timeline.
Events after the first event are not included in the at-risk journey. The
available data do not support a complete multi-state care pathway, and no
claims about transitions between outpatient, post-acute, or community-care
states are made.

## Event table contract

The enriched timeline contains:

| Column | Meaning |
|---|---|
| `subject_id` | Patient link key; sensitive/linkable, do not publish in reports |
| `hadm_id` | Admission link key; sensitive/linkable, do not publish in reports |
| `event_type` | One of the event types above except `death`, which is added to the bounded journey |
| `event_time` | Source timestamp or documented date-level proxy |
| `event_description` | Admission type, discharge location, or diagnosis dictionary title |
| `event_order` | Deterministic tie ordering: discharge, admission, then diagnosis |

The bounded journey adds index and outcome metadata, `followup_end_date`,
`window_end`, `days_from_index`, and `is_first_event`. Its time origin is
`index_dischtime`. It includes events on the discharge timestamp and through
the first-event timestamp or censor date, inclusive. A death event is explicit;
a first readmission is marked on its matching `hospital_admission` row.
Diagnosis events for a readmission may share that admission timestamp and are
encounter codes, not independent outcomes.

## Ordering and validation

The enriched table is sorted by patient, event time, event order, and
admission identifier. This gives stable ordering for equal timestamps without
asserting a causal order between same-time events. The bounded journey checks
that cohort patients are unique, event codes/dates are consistent, follow-up
does not exceed the configured horizon, and each readmission event matches an
admission row in the source timeline. A same-calendar-day death/readmission
ordering is limited by date-only death precision and the cohort builder's
conservative death tie rule.

## Reproduction

After creating a validated cohort with explicit `followup_end_date`, build the
enriched table, then the bounded journey:

```bash
python -m src.timeline.build_enriched_timeline \
  --cohort data/processed/cohort_phase3.csv \
  --output data/processed/timeline_phase4.csv
python -m src.timeline.create_observation_window \
  --cohort data/processed/cohort_phase3.csv \
  --timeline data/processed/timeline_phase4.csv \
  --output data/processed/journey_phase4.csv
```

Both commands refuse to replace existing files unless `--overwrite` is passed.
They print aggregate counts only. They do not fetch source data.

The current workspace includes `patients.csv.gz`, and the cohort builder can
produce a validated demo cohort with an explicit administrative end date. The
current steps generate the enriched event timeline and first-event observation
window from that cohort. Do not treat the resulting journey as clinically
validated or as a general population model; it is a prototype dataset built
from the demo extract and should be interpreted with the provenance and
censoring limitations described elsewhere in the project.
