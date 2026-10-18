"""Build the hospital-only projection of the canonical event timeline."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.data.validate_inputs import DEFAULT_DATA_DIR
from src.timeline.build_enriched_timeline import (
    COHORT_PATH,
    OUTPUT_PATH as ENRICHED_OUTPUT_PATH,
    REPOSITORY_ROOT,
    build_enriched_timeline,
)


OUTPUT_PATH = REPOSITORY_ROOT / "data/processed/patient_timeline.csv"


def build_timeline(
    admissions: pd.DataFrame,
    diagnoses: pd.DataFrame,
    diagnosis_dictionary: pd.DataFrame,
    cohort: pd.DataFrame,
) -> pd.DataFrame:
    """Return admission/discharge events from the shared canonical builder."""
    timeline = build_enriched_timeline(
        admissions, diagnoses, diagnosis_dictionary, cohort
    )
    return timeline.loc[
        timeline["event_type"].isin(
            ["hospital_admission", "hospital_discharge"]
        )
    ].reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the hospital-only patient timeline."
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

    missing = [
        filename
        for filename in (
            "admissions.csv.gz",
            "diagnoses_icd.csv.gz",
            "d_icd_diagnoses.csv.gz",
        )
        if not (args.data_dir / filename).is_file()
    ]
    if missing:
        parser.error(
            f"missing timeline inputs in {args.data_dir}: {', '.join(missing)}"
        )

    cohort_path = args.cohort
    if not cohort_path.is_absolute():
        cohort_path = REPOSITORY_ROOT / cohort_path
    timeline = build_timeline(
        pd.read_csv(args.data_dir / "admissions.csv.gz"),
        pd.read_csv(args.data_dir / "diagnoses_icd.csv.gz"),
        pd.read_csv(args.data_dir / "d_icd_diagnoses.csv.gz"),
        pd.read_csv(cohort_path),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    timeline.to_csv(output_path, index=False)
    print(
        f"Timeline events: {len(timeline)}; patients: "
        f"{timeline['subject_id'].nunique()}; saved to: {output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
