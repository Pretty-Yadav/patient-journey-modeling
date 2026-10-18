# Phase 1 status report: repository audit and reproducible environment

## 1. What was already present

- The repository already contains a project-level README with setup guidance and workflow context in [README.md](../README.md).
- The dependency list exists in [requirements.txt](../requirements.txt) and includes scientific Python packages needed for survival modeling and ML tasks.
- The validation module is already present in [src/data/validate_inputs.py](../src/data/validate_inputs.py).
- The cohort builder already exists in [src/cohort/build_cohort.py](../src/cohort/build_cohort.py).
- Unit tests already exist for the core validation, cohort, and timeline logic under [tests/unit](../tests/unit).
- Local demo data appears to be present under [physionet.org/files/mimic-iv-demo/2.2/hosp](../physionet.org/files/mimic-iv-demo/2.2/hosp), including `patients.csv.gz`.

## 2. What I changed

- Created this status report at [reports/project_status_phase1.md](project_status_phase1.md).

## 3. Why the change was needed

The repository already had most of the Phase 1 artifacts, but the project status needed to be explicitly verified against the live workspace. The current evidence shows that the environment and local demo data are usable, but the installation reproducibility is not yet locked down and the repository documentation contains at least one stale statement about missing data.

## 4. Commands to run

From the repository root:

```bash
cd /workspaces/patient-journey-modeling
python --version
python -m src.data.validate_inputs
python -m unittest discover -s tests/unit -v
```

For a Python 3.12 virtual environment, the project’s documented setup is:

```bash
cd /workspaces/patient-journey-modeling
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m unittest discover -s tests/unit -v
```

## 5. Expected outputs

Expected outputs for a working setup are:

- the input validation script prints a summary for `patients.csv.gz`, `admissions.csv.gz`, `diagnoses_icd.csv.gz`, and `d_icd_diagnoses.csv.gz`
- the validator reports `No validation issues found.` when the local MIMIC-IV Demo data is present and valid
- the unit test command runs the repository test suite and completes with `OK`

## 6. Tests actually run and real results

I actually ran these commands:

```bash
cd /workspaces/patient-journey-modeling && python -m src.data.validate_inputs
```

Result:

```text
MIMIC-IV Demo input validation

patients.csv.gz: OK, rows=100
admissions.csv.gz: OK, rows=275
diagnoses_icd.csv.gz: OK, rows=4506
d_icd_diagnoses.csv.gz: OK, rows=109775

No validation issues found.
```

I also ran:

```bash
cd /workspaces/patient-journey-modeling && python -m unittest discover -s tests/unit -v
```

Result:

```text
Ran 13 tests in 0.454s

OK
```

## 7. Known issues and limitations

- The repository README currently contains a stale statement that the local MIMIC-IV demo data does not include `patients.csv.gz`; in this workspace the file is present and valid.
- The environment is running Python 3.14.2, while the project documentation recommends Python 3.12 as the starting point. The full dependency set is not yet validated on Python 3.14 in this repo.
- [requirements.txt](../requirements.txt) is dependency-based but not a lock file, so it is not yet a fully reproducible environment specification.
- There are uncommitted repo changes already present in the working tree; they should be treated as in-progress work rather than as a clean baseline.
- The validation step is useful for demo-data integrity, but it does not establish whether the data are complete for a clinically or administratively supported follow-up window.

## 8. Git status

Git status at the time of the audit showed the repository was already in a modified/untracked state, with many files staged or edited outside of this Phase 1 checkpoint. This means the working tree is not clean and should not be treated as a pristine repository state.

Current branch:

```text
## develop...origin/develop
```

Current status summary from the live workspace:

```text
 M README.md
 M docs/data_plan.md
 M requirements.txt
 M src/cohort/build_cohort.py
 M src/timeline/build_enriched_timeline.py
 M src/timeline/build_timeline.py
 M src/timeline/create_observation_window.py
 ?? docs/cohort_definition.md
 ?? docs/data_dictionary.md
 ?? docs/states_and_timeline.md
 ?? reports/data_quality_report.md
 ?? src/data/validate_inputs.py
 ?? src/timeline/create_landmark_dataset.py
 ?? tests/unit/test_build_cohort.py
 ?? tests/unit/test_create_landmark_dataset.py
 ?? tests/unit/test_data_validation.py
 ?? tests/unit/test_timeline.py
```

## 9. Decision

Decision: partially complete.

Reason: the repository audit and environment check succeeded, and the demo data validation and unit tests are working, but the reproducibility and documentation details still need tightening before this phase can be considered fully complete.

## 10. Next phase recommendation

The next phase to continue with is Phase 2: data ingestion, provenance, and validation. The repository has a working validation module and local data access, so the next step should focus on formalizing provenance, documenting source limitations, and confirming the dataset is suitable for the downstream cohort definition work.
