# Phase 5 status report: survival analysis

## 1. What was already present

- The repository already had a legacy Kaplan-Meier script at [src/survival/kaplan_meier.py](../src/survival/kaplan_meier.py), but it was a one-off script rather than a reusable module and it targeted an outdated cohort file path.
- The project already had a cohort artifact at [data/processed/cohort_phase3.csv](../data/processed/cohort_phase3.csv), with the required `time_to_event_days` and `event` columns for survival analysis.
- The dependency list in [requirements.txt](../requirements.txt) already included `lifelines`, which supports the Kaplan-Meier estimator used here.

## 2. What I changed

- Replaced the old script with a reusable survival-analysis module in [src/survival/kaplan_meier.py](../src/survival/kaplan_meier.py).
- Added unit tests in [tests/unit/test_survival_analysis.py](../tests/unit/test_survival_analysis.py) covering the binary event coding, the expected Kaplan-Meier value, and missing-column validation.
- Generated the actual Kaplan-Meier plot at [reports/kaplan_meier_overall.png](kaplan_meier_overall.png).
- Added this phase report at [reports/project_status_phase5.md](project_status_phase5.md).

## 3. Why the changes were needed

The existing Kaplan-Meier script was not a robust package module and did not clearly document the estimand. It also used a legacy cohort path that did not match the current project naming convention. The new implementation makes the estimand explicit: it estimates the probability of remaining event-free when the event is defined as any first readmission or death, and it treats death and readmission as a single composite event for this analysis.

## 4. Commands to run

From the repository root:

```bash
cd /workspaces/patient-journey-modeling
python -m src.survival.kaplan_meier \
  --cohort data/processed/cohort_phase3.csv \
  --output reports/kaplan_meier_overall.png \
  --time-points 30 90 180
```

To run the Phase 5 tests:

```bash
cd /workspaces/patient-journey-modeling
python -m unittest tests.unit.test_survival_analysis -v
```

## 5. Expected outputs

Expected outputs for this phase are:

- a reusable survival-analysis module with validated input handling
- a plot file at [reports/kaplan_meier_overall.png](kaplan_meier_overall.png)
- survival estimates for requested time points
- unit tests that validate the event coding and the curve logic

## 6. Tests actually run and real results

I actually ran the unit tests:

```text
Ran 3 tests in 0.017s

OK
```

I also ran the actual Kaplan-Meier analysis command on the live cohort and captured:

```text
Kaplan-Meier analysis: any first event
Patients in cohort: 23
Any-event count: 8
Censored count: 15
Survival probabilities at requested time points:
30 days: 0.739
90 days: 0.739
180 days: 0.652
Saved Kaplan-Meier curve to: /workspaces/patient-journey-modeling/reports/kaplan_meier_overall.png
```

## 7. Known issues and limitations

- This Kaplan-Meier analysis treats readmission and death as a single composite event. That is useful for an event-free survival estimand, but it is not a competing-risk analysis.
- It does not estimate the probability of readmission specifically in the presence of competing death.
- The demo cohort is still small and not clinically validated.
- The repository remains in an active uncommitted state.

## 8. Git status

The repository is still not in a clean state, consistent with the earlier project phases. This is expected while the project remains in active development.

## 9. Decision

Decision: partially complete.

Reason: the survival-analysis module and plot are working, the synthetic and live checks pass, and the estimand is clearly stated, but the broader project still needs the next phases and a cleaner repo baseline before it is fully complete.

## 10. Next phase recommendation

The next phase should be Phase 6: competing-risk analysis.
