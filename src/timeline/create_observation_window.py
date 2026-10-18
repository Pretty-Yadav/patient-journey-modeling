"""Restrict a patient event table to verified at-risk follow-up."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TIMELINE_PATH = REPOSITORY_ROOT / "data/processed/patient_enriched_timeline.csv"
COHORT_PATH = REPOSITORY_ROOT / "data/processed/cohort.csv"
OUTPUT_PATH = REPOSITORY_ROOT / "data/processed/patient_journey_180d.csv"
MAX_FOLLOWUP_DAYS = 180

TIMELINE_COLUMNS = {
    "subject_id",
    "hadm_id",
    "event_type",
    "event_time",
    "event_description",
}
COHORT_COLUMNS = {
    "subject_id",
    "index_hadm_id",
    "index_admittime",
    "index_dischtime",
    "event",
    "event_date",
    "followup_end_date",
}
JOURNEY_COLUMNS = [
    "subject_id",
    "hadm_id",
    "event_type",
    "event_time",
    "event_description",
    "index_hadm_id",
    "index_admittime",
    "index_dischtime",
    "event",
    "event_date",
    "followup_end_date",
    "window_end",
    "days_from_index",
    "is_first_event",
]


def create_observation_window(
    timeline: pd.DataFrame,
    cohort: pd.DataFrame,
    max_followup_days: int = MAX_FOLLOWUP_DAYS,
) -> pd.DataFrame:
    """Keep timeline events from index discharge through first event/censoring.

    The output requires a cohort with an explicit ``followup_end_date``.
    Events after a first readmission or death are excluded, since the patient
    is no longer at risk for the first-event estimand.
    """
    if not isinstance(max_followup_days, int) or max_followup_days <= 0:
        raise ValueError("max_followup_days must be a positive integer")
    _require_columns(timeline, TIMELINE_COLUMNS, "timeline")
    _require_columns(cohort, COHORT_COLUMNS, "cohort")
    if timeline["subject_id"].isna().any():
        raise ValueError("timeline contains missing subject_id values")
    if cohort["subject_id"].isna().any():
        raise ValueError("cohort contains missing subject_id values")
    if cohort["subject_id"].duplicated().any():
        raise ValueError("cohort contains duplicate subject_id values")

    timeline = timeline.copy()
    cohort = cohort.copy()
    timeline["event_time"] = _parse_dates(
        timeline["event_time"], "timeline.event_time"
    )
    for column in ("index_admittime", "index_dischtime", "followup_end_date"):
        cohort[column] = _parse_dates(cohort[column], f"cohort.{column}")
    cohort["event"] = pd.to_numeric(cohort["event"], errors="raise")
    if not cohort["event"].isin([0, 1, 2]).all():
        raise ValueError("cohort.event must contain only 0, 1, or 2")
    cohort["event_date"] = _parse_optional_dates(
        cohort["event_date"], "cohort.event_date"
    )
    if (cohort["index_dischtime"] > cohort["followup_end_date"]).any():
        raise ValueError("followup_end_date precedes index_dischtime")
    max_end = cohort["index_dischtime"] + pd.Timedelta(
        max_followup_days, unit="D"
    )
    if (cohort["followup_end_date"] > max_end).any():
        raise ValueError(
            "followup_end_date exceeds the configured follow-up horizon"
        )

    has_event = cohort["event"].ne(0)
    if (has_event & cohort["event_date"].isna()).any():
        raise ValueError("event rows must have an event_date")
    if ((~has_event) & cohort["event_date"].notna()).any():
        raise ValueError("censored rows must not have an event_date")
    if (
        has_event
        & (
            (cohort["event_date"] < cohort["index_dischtime"])
            | (cohort["event_date"] > cohort["followup_end_date"])
        )
    ).any():
        raise ValueError("event_date must be within index and follow-up bounds")

    cohort["window_end"] = cohort["followup_end_date"]
    cohort.loc[has_event, "window_end"] = cohort.loc[has_event, "event_date"]
    merged = timeline.merge(
        cohort[
            [
                "subject_id",
                "index_hadm_id",
                "index_admittime",
                "index_dischtime",
                "event",
                "event_date",
                "followup_end_date",
                "window_end",
            ]
        ],
        on="subject_id",
        how="inner",
        validate="many_to_one",
    )
    in_window = merged["event_time"].between(
        merged["index_dischtime"], merged["window_end"], inclusive="both"
    )
    journey = merged.loc[in_window].copy()
    journey["days_from_index"] = (
        journey["event_time"] - journey["index_dischtime"]
    ).dt.total_seconds() / 86400
    journey["is_first_event"] = False

    readmission_rows = journey["event"].eq(1) & journey["event_type"].eq(
        "hospital_admission"
    )
    readmission_rows &= journey["event_time"].eq(journey["event_date"])
    journey.loc[readmission_rows, "is_first_event"] = True

    for patient in cohort.loc[cohort["event"].eq(1)].itertuples(index=False):
        matching = journey.loc[
            journey["subject_id"].eq(patient.subject_id)
            & journey["event_type"].eq("hospital_admission")
            & journey["event_time"].eq(patient.event_date)
        ]
        if matching.empty:
            raise ValueError(
                "readmission event has no matching hospital_admission in timeline"
            )

    death_rows = cohort.loc[cohort["event"].eq(2), [
        "subject_id",
        "index_hadm_id",
        "index_admittime",
        "index_dischtime",
        "event_date",
        "followup_end_date",
        "window_end",
    ]].copy()
    if not death_rows.empty:
        death_rows["hadm_id"] = pd.NA
        death_rows["event_type"] = "death"
        death_rows["event_time"] = death_rows["event_date"]
        death_rows["event_description"] = "Recorded date of death"
        death_rows["event"] = 2
        death_rows["days_from_index"] = (
            death_rows["event_time"] - death_rows["index_dischtime"]
        ).dt.total_seconds() / 86400
        death_rows["is_first_event"] = True
        journey = pd.concat([journey, death_rows], ignore_index=True)

    journey = journey[JOURNEY_COLUMNS].sort_values(
        ["subject_id", "event_time", "event_type", "hadm_id"],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)
    return journey


def _require_columns(
    table: pd.DataFrame, required: set[str], table_name: str
) -> None:
    missing = required.difference(table.columns)
    if missing:
        raise ValueError(
            f"{table_name} is missing required columns: {sorted(missing)}"
        )


def _parse_dates(values: pd.Series, label: str) -> pd.Series:
    parsed = pd.to_datetime(values, format="mixed", errors="coerce")
    if parsed.isna().any():
        raise ValueError(f"{label} contains missing or invalid dates")
    return parsed


def _parse_optional_dates(values: pd.Series, label: str) -> pd.Series:
    parsed = pd.to_datetime(values, format="mixed", errors="coerce")
    if (values.notna() & parsed.isna()).any():
        raise ValueError(f"{label} contains invalid dates")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build at-risk patient journeys from index discharge."
    )
    parser.add_argument("--timeline", type=Path, default=TIMELINE_PATH)
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

    timeline_path = args.timeline
    cohort_path = args.cohort
    if not timeline_path.is_absolute():
        timeline_path = REPOSITORY_ROOT / timeline_path
    if not cohort_path.is_absolute():
        cohort_path = REPOSITORY_ROOT / cohort_path
    journey = create_observation_window(
        pd.read_csv(timeline_path),
        pd.read_csv(cohort_path),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    journey.to_csv(output_path, index=False)
    print(
        f"Journey events: {len(journey)}; patients: "
        f"{journey['subject_id'].nunique()}; saved to: {output_path}"
    )
    print("Event types:")
    print(journey["event_type"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
