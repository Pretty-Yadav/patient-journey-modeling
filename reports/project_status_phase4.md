# Phase 4 status report: clinical states and event timeline

## 1. What was already present

- The timeline builder already existed in [src/timeline/build_enriched_timeline.py](../src/timeline/build_enriched_timeline.py).
- The observation-window builder already existed in [src/timeline/create_observation_window.py](../src/timeline/create_observation_window.py).
- The state/timeline documentation already existed in [docs/states_and_timeline.md](../docs/states_and_timeline.md).
- The unit tests for the timeline logic already existed in [tests/unit/test_timeline.py](../tests/unit/test_timeline.py).
- The project already had a valid cohort output in [data/processed/cohort_phase3.csv](../data/processed/cohort_phase3.csv).

## 2. What I changed

- Corrected stale state/timeline documentation in [docs/states_and_timeline.md](../docs/states_and_timeline.md) so it matches the actual verified demo-data workflow.
- Generated the live timeline and journey outputs:
  - [data/processed/timeline_phase4.csv](../data/processed/timeline_phase4.csv)
  - [data/processed/journey_phase4.csv](../data/processed/journey_phase4.csv)
- Added this status report at [reports/project_status_phase4.md](project_status_phase4.md).

## 3. Why the changes were needed

Phase 4 was already largely implemented, but the state/timeline documentation still described an outdated missing-data situation. I verified the actual timeline pipeline on the current cohort and generated the event table and bounded observation window from the live demo data.

## 4. Commands to run

From the repo root:

```bash
cd /workspaces/patient-journey-modeling
python -m src.timeline.build_enriched_timeline \
  --cohort data/processed/cohort_phase3.csv \
  --output data/processed/timeline_phase4.csv \
  --overwrite
python -m src.timeline.create_observation_window \
  --cohort data/processed/cohort_phase3.csv \
  --timeline data/processed/timeline_phase4.csv \
  --output data/processed/journey_phase4.csv \
  --overwrite
```

The repository smoke test remains:

```bash
cd /workspaces/patient-journey-modeling
python -m unittest discover -s tests/unit -v
```

## 5. Expected outputs

- a patient event timeline at [data/processed/timeline_phase4.csv](../data/processed/timeline_phase4.csv)
- a first-event bounded observation window at [data/processed/journey_phase4.csv](../data/processed/journey_phase4.csv)
- event ordering and censoring consistent with the cohort's `followup_end_date`

## 6. Tests actually run and real results

I ran the actual timeline generation commands and got:

```text
Timeline events: 2504; patients: 23; saved to: /workspaces/patient-journey-modeling/data/processed/timeline_phase4.csv
Event counts:
event_type
diagnosis             2280
hospital_admission     112
hospital_discharge     112
Journey events: 148; patients: 23; saved to: /workspaces/patient-journey-modeling/data/processed/journey_phase4.csv
Event types:
event_type
diagnosis             117
hospital_discharge     23
hospital_admission      7
death                   1
```

I also ran the unit tests again:

```text
Ran 13 tests in 0.363s

OK
```

## 7. Known issues and limitations

- Diagnosis rows are assigned an admission timestamp as an encounter-time proxy; they are not true diagnostic onset times.
- The phase still relies on a local demo dataset and is not a clinically validated pathway model.
- The project still has no full provenance chain for source checksums or acquisition metadata.
- The repo is not in a clean Git state.

## 8. Git status

The repository remains unclean and contains other in-progress changes beyond this phase. That status is part of the live workspace and should be treated as such.

## 9. Decision

Decision: partially complete.

Reason: the timeline and journey generation are working end-to-end, but the project still needs stronger provenance and baseline cleanliness before it can be considered fully complete as a general-purpose prototype.

## 10. Next phase recommendation

The next phase should be Phase 5: survival analysis.
