# Phase 3 status report: cohort definition and index date

## 1. What was already present

- The cohort builder already existed in [src/cohort/build_cohort.py](../src/cohort/build_cohort.py).
- The unit tests for cohort logic already existed in [tests/unit/test_build_cohort.py](../tests/unit/test_build_cohort.py).
- The cohort definition documentation already existed in [docs/cohort_definition.md](../docs/cohort_definition.md).
- The repository already contained a local MIMIC-IV Demo data extract and the validation module in [src/data/validate_inputs.py](../src/data/validate_inputs.py).
- The cohort logic already encoded the required rules: one row per patient, earliest heart-failure event as the index admission, explicit administrative end date, exclusion of in-hospital death or death on or before index discharge, and competing readmission/death outcomes.

## 2. What I changed

- Corrected stale cohort-definition wording in [docs/cohort_definition.md](../docs/cohort_definition.md) so it matches the verified local source state.
- Generated a live cohort result at [data/processed/cohort_phase3.csv](../data/processed/cohort_phase3.csv) using the current demo extract.
- Created this status report at [reports/project_status_phase3.md](project_status_phase3.md).

## 3. Why the changes were needed

The implementation was already close to a valid Phase 3 prototype, but the documentation had drifted and still claimed the needed patient file was missing. I verified the real workspace state and ran the actual cohort builder to confirm that the prototype logic works with the local MIMIC-IV Demo data.

## 4. Commands to run

From the repository root:

```bash
cd /workspaces/patient-journey-modeling
python -m src.cohort.build_cohort \
  --data-dir physionet.org/files/mimic-iv-demo/2.2/hosp \
  --administrative-end-date 2201-12-17 \
  --output data/processed/cohort_phase3.csv \
  --overwrite
```

The lightweight project smoke test is still:

```bash
cd /workspaces/patient-journey-modeling
python -m unittest discover -s tests/unit -v
```

## 5. Expected outputs

Expected outputs for this phase are:

- a cohort CSV at [data/processed/cohort_phase3.csv](../data/processed/cohort_phase3.csv)
- aggregate flow counts showing `patients_in_source`, `patients_with_heart_failure_diagnosis`, `patients_with_eligible_index_admission`, `excluded_death_during_or_on_index_discharge`, `patients_in_cohort`, `readmission_events`, `death_events`, and `censored`
- a final cohort with one row per patient and a valid `followup_end_date` and `administrative_end_date`

## 6. Tests actually run and real results

I ran the cohort build command and captured the actual output:

```text
Cohort flow (aggregate counts only):
patients_in_source: 100
patients_with_heart_failure_diagnosis: 24
patients_with_eligible_index_admission: 24
excluded_death_during_or_on_index_discharge: 1
patients_in_cohort: 23
readmission_events: 7
death_events: 1
censored: 15
```

I also ran the unit tests again after the phase work:

```text
Ran 13 tests in 0.363s

OK
```

## 7. Known issues and limitations

- This is still a prototype cohort, not a clinically validated heart-failure registry.
- The diagnosis-title heuristic is a local rule, not a validated clinical phenotype.
- The study assumes complete hospital admission capture within the available hospital dataset and does not establish external readmission capture or coverage beyond this source.
- The administrative end date must be justified from source provenance before any real-world interpretation.
- The repo is currently in an active, modified state and is not a clean baseline.

## 8. Git status

Git remains unclean in the current workspace. The phase work created and modified files, but the repository still contains other ongoing in-progress edits.

## 9. Decision

Decision: partially complete.

Reason: the cohort logic and output generation are working, and the script has been validated on the current demo data, but this repo still requires stronger provenance documentation and clean baseline management before it is fully complete as a reusable prototype.

## 10. Next phase recommendation

The next phase should be Phase 4: clinical states and event timeline.
