"""Build a chronological admission, discharge, and diagnosis event table."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.data.validate_inputs import DEFAULT_DATA_DIR


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
COHORT_PATH = REPOSITORY_ROOT / "data/processed/cohort.csv"
OUTPUT_PATH = REPOSITORY_ROOT / "data/processed/patient_enriched_timeline.csv"

EVENT_ORDER = {
    "hospital_discharge": 0,
    "hospital_admission": 1,
    "diagnosis": 2,
}
TIMELINE_COLUMNS = [
    "subject_id",
    "hadm_id",
    "event_type",
    "event_time",
    "event_description",
    "event_order",
]


def build_enriched_timeline(
    admissions: pd.DataFrame,
    diagnoses: pd.DataFrame,
    diagnosis_dictionary: pd.DataFrame,
    cohort: pd.DataFrame,
) -> pd.DataFrame:
    """Build a stable event table for admissions belonging to cohort patients.

    Diagnosis records are assigned their admission timestamp as an encounter-
    level proxy. This is not an assertion that each diagnosis began at that
    instant or that the code was known at every time during the admission.
    """
    _require_columns(
        admissions,
        {
            "subject_id",
            "hadm_id",
            "admittime",
            "dischtime",
            "admission_type",
            "discharge_location",
        },
        "admissions",
    )
    _require_columns(
        diagnoses,
        {"subject_id", "hadm_id", "icd_code", "icd_version"},
        "diagnoses",
    )
    _require_columns(
        diagnosis_dictionary,
        {"icd_code", "icd_version", "long_title"},
        "diagnosis_dictionary",
    )
    _require_columns(cohort, {"subject_id"}, "cohort")
    _require_unique(cohort, ["subject_id"], "cohort")
    _require_unique(admissions, ["hadm_id"], "admissions")
    _require_unique(
        diagnosis_dictionary, ["icd_code", "icd_version"], "diagnosis_dictionary"
    )

    patient_ids = set(cohort["subject_id"].dropna())
    if cohort["subject_id"].isna().any():
        raise ValueError("cohort contains missing subject_id values")

    admission_rows = admissions.loc[
        admissions["subject_id"].isin(patient_ids)
    ].copy()
    admission_rows["admittime"] = _parse_dates(
        admission_rows["admittime"], "admissions.admittime"
    )
    admission_rows["dischtime"] = _parse_dates(
        admission_rows["dischtime"], "admissions.dischtime"
    )
    if (admission_rows["dischtime"] < admission_rows["admittime"]).any():
        raise ValueError("admissions contains discharge before admission")

    admission_keys = admission_rows[["subject_id", "hadm_id"]].drop_duplicates()
    patient_diagnoses = diagnoses.loc[
        diagnoses["subject_id"].isin(patient_ids)
    ].copy()
    diagnosis_keys = patient_diagnoses[["subject_id", "hadm_id"]].drop_duplicates()
    linked_keys = diagnosis_keys.merge(
        admission_keys,
        on=["subject_id", "hadm_id"],
        how="left",
        indicator=True,
        validate="one_to_one",
    )
    if (linked_keys["_merge"] == "left_only").any():
        count = int((linked_keys["_merge"] == "left_only").sum())
        raise ValueError(
            f"{count} diagnosis subject/admission pairs are absent from timeline admissions"
        )

    diagnoses_with_titles = patient_diagnoses.merge(
        diagnosis_dictionary,
        on=["icd_code", "icd_version"],
        how="left",
        validate="many_to_one",
    )
    if diagnoses_with_titles["long_title"].isna().any():
        missing = int(diagnoses_with_titles["long_title"].isna().sum())
        raise ValueError(f"{missing} diagnosis rows have no dictionary title")
    diagnoses_with_admission = diagnoses_with_titles.merge(
        admission_rows[
            ["subject_id", "hadm_id", "admittime"]
        ],
        on=["subject_id", "hadm_id"],
        how="left",
        validate="many_to_one",
    )

    rows: list[pd.DataFrame] = []
    hospital_admissions = admission_rows[
        [
            "subject_id",
            "hadm_id",
            "admittime",
            "admission_type",
            "discharge_location",
        ]
    ].rename(
        columns={
            "admittime": "event_time",
            "admission_type": "event_description",
        }
    )
    hospital_admissions["event_type"] = "hospital_admission"
    hospital_admissions["event_order"] = EVENT_ORDER["hospital_admission"]
    rows.append(hospital_admissions[TIMELINE_COLUMNS])

    hospital_discharges = admission_rows[
        [
            "subject_id",
            "hadm_id",
            "dischtime",
            "discharge_location",
        ]
    ].rename(
        columns={
            "dischtime": "event_time",
            "discharge_location": "event_description",
        }
    )
    hospital_discharges["event_type"] = "hospital_discharge"
    hospital_discharges["event_order"] = EVENT_ORDER["hospital_discharge"]
    rows.append(hospital_discharges[TIMELINE_COLUMNS])

    diagnosis_events = diagnoses_with_admission[
        ["subject_id", "hadm_id", "admittime", "long_title"]
    ].rename(
        columns={
            "admittime": "event_time",
            "long_title": "event_description",
        }
    )
    diagnosis_events["event_type"] = "diagnosis"
    diagnosis_events["event_order"] = EVENT_ORDER["diagnosis"]
    rows.append(diagnosis_events[TIMELINE_COLUMNS])

    timeline = pd.concat(rows, ignore_index=True)
    timeline["event_time"] = _parse_dates(
        timeline["event_time"], "timeline.event_time"
    )
    return timeline.sort_values(
        ["subject_id", "event_time", "event_order", "hadm_id"],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)


def _require_columns(
    table: pd.DataFrame, required: set[str], table_name: str
) -> None:
    missing = required.difference(table.columns)
    if missing:
        raise ValueError(
            f"{table_name} is missing required columns: {sorted(missing)}"
        )


def _require_unique(
    table: pd.DataFrame, columns: list[str], table_name: str
) -> None:
    if table.duplicated(columns).any():
        raise ValueError(
            f"{table_name} contains duplicate keys: {', '.join(columns)}"
        )


def _parse_dates(values: pd.Series, label: str) -> pd.Series:
    parsed = pd.to_datetime(values, format="mixed", errors="coerce")
    if parsed.isna().any():
        raise ValueError(f"{label} contains missing or invalid dates")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the chronological enriched patient event timeline."
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--cohort", type=Path, default=COHORT_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    output_path = args.output
    if not output_path.is_absolute():
        output_path = REPOSITORY_ROOT / output_path
    if output_path.exists() and not args.overwrite:
        parser.error(
            f"output already exists: {output_path}; use another --output "
            "or pass --overwrite after reviewing it"
        )

    cohort_path = args.cohort
    if not cohort_path.is_absolute():
        cohort_path = REPOSITORY_ROOT / cohort_path
    required_files = [
        "admissions.csv.gz",
        "diagnoses_icd.csv.gz",
        "d_icd_diagnoses.csv.gz",
    ]
    missing = [name for name in required_files if not (args.data_dir / name).is_file()]
    if missing:
        parser.error(f"missing timeline inputs in {args.data_dir}: {', '.join(missing)}")
    cohort = pd.read_csv(cohort_path)
    timeline = build_enriched_timeline(
        pd.read_csv(args.data_dir / "admissions.csv.gz"),
        pd.read_csv(args.data_dir / "diagnoses_icd.csv.gz"),
        pd.read_csv(args.data_dir / "d_icd_diagnoses.csv.gz"),
        cohort,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    timeline.to_csv(output_path, index=False)
    print(
        f"Timeline events: {len(timeline)}; patients: "
        f"{timeline['subject_id'].nunique()}; saved to: {output_path}"
    )
    print("Event counts:")
    print(timeline["event_type"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
