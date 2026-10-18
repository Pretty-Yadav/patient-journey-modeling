# Patient Journey Modeling

A research prototype for analyzing longitudinal patient journeys and modeling post-discharge outcomes using competing risks and care-pathway features. It includes data-preparation pipelines, baseline model outputs, an API, and an interactive Streamlit dashboard.

This project uses MIMIC-IV Demo data and is not clinical decision support. Use only data and derived outputs that you are authorized to process and publish.

## Quick Start

Use Python 3.12. From the repository root, install the dashboard dependencies and run the app:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

Open <http://localhost:8501>. The dashboard reads available CSV and image artifacts directly from `data/processed/` and `reports/`; it does not require the API to run. It prefers `cohort_phase3.csv` and falls back to the tracked `cohort.csv` when the phase-3 artifact is not present. If optional artifacts are absent, their dashboard sections will be empty or show zero counts.

To run the API separately, install the app dependencies and start Uvicorn:

```bash
python -m pip install -r requirements-app.txt
uvicorn api.main:app --host 127.0.0.1 --port 8001
```

The API health endpoint is <http://127.0.0.1:8001/health>; its summary is at <http://127.0.0.1:8001/summary>.

Alternatively, run both services with Docker Compose:

```bash
docker compose up --build -d
```

Open <http://localhost:8501>. Stop the containers with `docker compose down`.

## Streamlit Community Cloud

The dashboard can run on Community Cloud without a separately hosted API. Its lightweight dependency file is `dashboard/requirements.txt`, and it reads artifact files from the deployed repository checkout.

1. Push the project to a GitHub repository and make sure the branch contains `dashboard/app.py` and `dashboard/requirements.txt`.
2. Sign in at [Streamlit Community Cloud](https://share.streamlit.io/) with GitHub and choose **Create app**.
3. Select the repository and branch, and set **Main file path** to `dashboard/app.py`.
4. Select Python 3.12 in the advanced settings, then deploy.

No API URL or secrets are required for this dashboard configuration. Community Cloud only receives files committed to the selected GitHub branch; files present only in your Codespace are not deployed. The committed `data/processed/cohort.csv` is used automatically when `cohort_phase3.csv` is absent. To populate prediction and evaluation sections, include the approved `data/processed/xgboost_predictions.csv`, `reports/xgboost_feature_importance.csv`, `reports/subgroup_analysis.csv`, and optionally `reports/xgboost_calibration.png`.

Before publishing, confirm that you have permission to host every artifact. Do not commit raw MIMIC-IV data or patient-level records to a public repository or public app. The dashboard includes prediction records, so check the repository and app visibility and the applicable data-use terms; prefer approved aggregate outputs for public demos.

## Project Workflow

### Validate source data

The validator checks the required MIMIC-IV Demo hospital tables and reports aggregate schema, key, date, and referential-integrity checks:

```bash
python -m src.data.validate_inputs
```

Pass `--data-dir /path/to/mimic-iv-demo/2.2/hosp` to validate another local copy. The command does not create or modify datasets.

### Build cohort and timelines

After validation and establishing a source-supported administrative complete-through date, build the cohort:

```bash
python -m src.cohort.build_cohort \
  --administrative-end-date YYYY-MM-DD \
  --output data/processed/cohort_phase3.csv
```

The required date must come from source documentation; it is not safe to assume a fixed follow-up period. After creating a cohort with `followup_end_date`, build its enriched timeline and observation window:

```bash
python -m src.timeline.build_enriched_timeline \
  --cohort data/processed/cohort_phase3.csv \
  --output data/processed/timeline_phase4.csv
python -m src.timeline.create_observation_window \
  --cohort data/processed/cohort_phase3.csv \
  --timeline data/processed/timeline_phase4.csv \
  --output data/processed/journey_phase4.csv
```

These commands refuse to overwrite existing outputs unless explicitly instructed. See [the cohort definition](docs/cohort_definition.md) and [state and timeline definitions](docs/states_and_timeline.md) for assumptions and limitations.

### Landmark dataset

After preparing the cohort and 180-day journey, create the 30- and 90-day landmark rows:

```bash
python src/timeline/create_landmark_dataset.py
```

Patients can contribute two rows, so split by `subject_id` to prevent a patient's records appearing in both train and test sets. See [the evaluation protocol](docs/evaluation_protocol.md) for validation guidance.

## Development and Tests

Install the broader scientific and pipeline dependencies with Python 3.12:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests/unit -v
```

Run pipeline commands from the repository root because their input and output paths are relative to it. Dependency ranges are not a lock file. See [the data plan](docs/data_plan.md), [data dictionary](docs/data_dictionary.md), and [data quality report](reports/data_quality_report.md) for provenance and schemas.
