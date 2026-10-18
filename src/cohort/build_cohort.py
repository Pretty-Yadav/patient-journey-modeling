"""Construct a heart-failure admission cohort from local MIMIC-IV Demo tables."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.data.validate_inputs import DEFAULT_DATA_DIR, validate_inputs


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_PATH = REPOSITORY_ROOT / "data/processed/cohort.csv"
MAX_FOLLOWUP_DAYS = 180
EVENT_LABELS = {
    0: "censored",
    1: "readmission",
    2: "death",
}


def build_cohort(
    patients: pd.DataFrame,
    admissions: pd.DataFrame,
    diagnoses: pd.DataFrame,
    diagnosis_dictionary: pd.DataFrame,
    administrative_end_date: str | pd.Timestamp,
    max_followup_days: int = MAX_FOLLOWUP_DAYS,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Build one post-discharge observation per patient.

    Heart failure eligibility is determined by an ICD diagnosis on an
    admission, using the existing title-based code definition. Index is the
    patient's earliest such admission. Readmission means any later admission
    in the supplied hospital admissions table after index discharge. Death
    and readmission are competing first events. Follow-up is administratively
    censored at the explicitly supplied complete-through date or at the
    maximum follow-up horizon, whichever comes first.

    A date-only administrative end is inclusive through the end of that
    calendar day. The caller is responsible for supplying a date supported by
    source provenance and complete outcome ascertainment.
    """
    if not isinstance(max_followup_days, int) or max_followup_days <= 0:
        raise ValueError("max_followup_days must be a positive integer")

    _require_columns(
        patients,
        {"subject_id", "gender", "anchor_age", "dod"},
        "patients",
    )
    _require_columns(
        admissions,
        {
            "subject_id",
            "hadm_id",
            "admittime",
            "dischtime",
            "hospital_expire_flag",
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

    end_of_observation = _parse_administrative_end(administrative_end_date)
    patients = patients.copy()
    admissions = admissions.copy()
    diagnoses = diagnoses.copy()
    diagnosis_dictionary = diagnosis_dictionary.copy()

    _require_unique(patients, ["subject_id"], "patients")
    _require_unique(admissions, ["hadm_id"], "admissions")
    _require_unique(
        diagnosis_dictionary,
        ["icd_code", "icd_version"],
        "diagnosis_dictionary",
    )
    if patients["subject_id"].isna().any():
        raise ValueError("patients contains missing subject_id values")
    if admissions[["subject_id", "hadm_id"]].isna().any().any():
        raise ValueError("admissions contains missing subject_id or hadm_id")

    admissions["admittime"] = _parse_required_dates(
        admissions["admittime"], "admissions.admittime"
    )
    admissions["dischtime"] = _parse_required_dates(
        admissions["dischtime"], "admissions.dischtime"
    )
    patients["dod"] = _parse_optional_dates(patients["dod"], "patients.dod")
    admissions["hospital_expire_flag"] = pd.to_numeric(
        admissions["hospital_expire_flag"], errors="raise"
    )
    if not admissions["hospital_expire_flag"].isin([0, 1]).all():
        raise ValueError("hospital_expire_flag must contain only 0 or 1")
    if (admissions["dischtime"] < admissions["admittime"]).any():
        raise ValueError("admissions contains discharge before admission")

    patient_ids = set(patients["subject_id"])
    orphan_subjects = set(admissions["subject_id"]).difference(patient_ids)
    if orphan_subjects:
        raise ValueError(
            f"{len(orphan_subjects)} admission subjects are absent from patients"
        )

    admission_keys = admissions[["subject_id", "hadm_id"]].drop_duplicates()
    diagnosis_keys = diagnoses[["subject_id", "hadm_id"]].drop_duplicates()
    linked_diagnoses = diagnosis_keys.merge(
        admission_keys,
        on=["subject_id", "hadm_id"],
        how="left",
        indicator=True,
        validate="one_to_one",
    )
    if (linked_diagnoses["_merge"] == "left_only").any():
        count = int((linked_diagnoses["_merge"] == "left_only").sum())
        raise ValueError(
            f"{count} diagnosis subject/admission pairs are absent from admissions"
        )

    heart_failure_codes = diagnosis_dictionary[
        diagnosis_dictionary["long_title"].str.contains(
            "heart failure", case=False, na=False
        )
        & ~diagnosis_dictionary["long_title"].str.contains(
            "without heart failure", case=False, na=False
        )
    ][["icd_code", "icd_version"]]
    if heart_failure_codes.empty:
        raise ValueError("No heart-failure diagnosis codes found in dictionary")

    qualifying_diagnoses = diagnoses.merge(
        heart_failure_codes,
        on=["icd_code", "icd_version"],
        how="inner",
        validate="many_to_one",
    )
    if qualifying_diagnoses.empty:
        raise ValueError("No heart-failure-coded admissions found")

    qualifying_keys = qualifying_diagnoses[
        ["subject_id", "hadm_id"]
    ].drop_duplicates()
    qualifying_admissions = admissions.merge(
        qualifying_keys,
        on=["subject_id", "hadm_id"],
        how="inner",
        validate="one_to_one",
    )
    index_admissions = (
        qualifying_admissions.sort_values(
            ["subject_id", "admittime", "hadm_id"], kind="stable"
        )
        .drop_duplicates("subject_id", keep="first")
        .rename(
            columns={
                "hadm_id": "index_hadm_id",
                "admittime": "index_admittime",
                "dischtime": "index_dischtime",
            }
        )
    )

    cohort = index_admissions[
        [
            "subject_id",
            "index_hadm_id",
            "index_admittime",
            "index_dischtime",
            "hospital_expire_flag",
        ]
    ].merge(
        patients[["subject_id", "gender", "anchor_age", "dod"]],
        on="subject_id",
        how="left",
        validate="one_to_one",
    )

    if (cohort["index_dischtime"] > end_of_observation).any():
        raise ValueError(
            "administrative_end_date precedes one or more index discharges"
        )

    died_during_index = cohort["hospital_expire_flag"].eq(1) | (
        cohort["dod"].notna()
        & (cohort["dod"].dt.normalize() <= cohort["index_dischtime"].dt.normalize())
    )
    excluded_in_hospital_death = int(died_during_index.sum())
    cohort = cohort.loc[~died_during_index].copy()
    cohort.drop(columns="hospital_expire_flag", inplace=True)

    admissions_by_subject = {
        subject_id: group.sort_values(
            ["admittime", "hadm_id"], kind="stable"
        )
        for subject_id, group in admissions.groupby("subject_id", sort=False)
    }

    readmission_dates = []
    event_codes = []
    event_dates = []
    followup_end_dates = []
    durations = []

    for row in cohort.itertuples(index=False):
        index_discharge = row.index_dischtime
        horizon_end = index_discharge + pd.Timedelta(
            max_followup_days, unit="D"
        )
        followup_end = min(horizon_end, end_of_observation)
        followup_end_dates.append(followup_end)

        patient_admissions = admissions_by_subject[row.subject_id]
        subsequent = patient_admissions.loc[
            (patient_admissions["admittime"] > index_discharge)
            & (patient_admissions["admittime"] <= followup_end)
        ]
        readmission_date = (
            subsequent["admittime"].min()
            if not subsequent.empty
            else pd.NaT
        )
        readmission_dates.append(readmission_date)

        death_date = row.dod.normalize() if pd.notna(row.dod) else pd.NaT
        possible_events = []
        if pd.notna(readmission_date):
            possible_events.append((readmission_date, 1))
        if (
            pd.notna(death_date)
            and death_date > index_discharge
            and death_date <= followup_end
        ):
            possible_events.append((death_date, 2))

        if possible_events:
            # Death is date-only; for a same-day readmission/death pair,
            # event ordering is unknowable, so assign death conservatively.
            first_date, first_event = min(
                possible_events,
                key=lambda item: (
                    item[0].normalize(),
                    0 if item[1] == 2 else 1,
                    item[0],
                ),
            )
            event_codes.append(first_event)
            event_dates.append(first_date)
            durations.append(
                (first_date - index_discharge).total_seconds() / 86400
            )
        else:
            event_codes.append(0)
            event_dates.append(pd.NaT)
            durations.append(
                (followup_end - index_discharge).total_seconds() / 86400
            )

    cohort["readmission_date"] = readmission_dates
    cohort["event"] = event_codes
    cohort["event_date"] = event_dates
    cohort["time_to_event_days"] = durations
    cohort["event_label"] = cohort["event"].map(EVENT_LABELS)
    cohort["followup_end_date"] = followup_end_dates
    cohort["administrative_end_date"] = end_of_observation

    cohort = cohort.sort_values("subject_id").reset_index(drop=True)
    if cohort["subject_id"].duplicated().any():
        raise AssertionError("cohort construction produced duplicate patients")
    if (cohort["time_to_event_days"] < 0).any():
        raise AssertionError("cohort construction produced negative follow-up")

    flow = {
        "patients_in_source": int(patients["subject_id"].nunique()),
        "patients_with_heart_failure_diagnosis": int(
            qualifying_keys["subject_id"].nunique()
        ),
        "patients_with_eligible_index_admission": int(
            index_admissions["subject_id"].nunique()
        ),
        "excluded_death_during_or_on_index_discharge": excluded_in_hospital_death,
        "patients_in_cohort": int(len(cohort)),
        "readmission_events": int(cohort["event"].eq(1).sum()),
        "death_events": int(cohort["event"].eq(2).sum()),
        "censored": int(cohort["event"].eq(0).sum()),
    }
    return cohort, flow


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


def _parse_required_dates(values: pd.Series, label: str) -> pd.Series:
    parsed = pd.to_datetime(values, format="mixed", errors="coerce")
    invalid = int(parsed.isna().sum())
    if invalid:
        raise ValueError(f"{label} has {invalid} missing or invalid dates")
    return parsed


def _parse_optional_dates(values: pd.Series, label: str) -> pd.Series:
    parsed = pd.to_datetime(values, format="mixed", errors="coerce")
    invalid = int((values.notna() & parsed.isna()).sum())
    if invalid:
        raise ValueError(f"{label} has {invalid} invalid dates")
    return parsed


def _parse_administrative_end(
    administrative_end_date: str | pd.Timestamp,
) -> pd.Timestamp:
    try:
        parsed = pd.Timestamp(administrative_end_date)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "administrative_end_date must be an ISO date or timestamp"
        ) from exc
    if pd.isna(parsed):
        raise ValueError("administrative_end_date cannot be missing")
    if parsed.tz is not None:
        raise ValueError("administrative_end_date must not include a timezone")
    if isinstance(administrative_end_date, str) and len(
        administrative_end_date.strip()
    ) == 10:
        parsed = (
            parsed.normalize()
            + pd.Timedelta(1, unit="D")
            - pd.Timedelta(1, unit="ns")
        )
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a heart-failure index-admission cohort."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing the four required MIMIC-IV Demo CSV files.",
    )
    parser.add_argument(
        "--administrative-end-date",
        required=True,
        help=(
            "Verified date through which the source has complete observation "
            "(YYYY-MM-DD is inclusive through end of day)."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Cohort CSV output path (default: data/processed/cohort.csv).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing output file.",
    )
    args = parser.parse_args()

    output_path = args.output
    if not output_path.is_absolute():
        output_path = REPOSITORY_ROOT / output_path
    if output_path.exists() and not args.overwrite:
        parser.error(
            f"output already exists: {output_path}; select another --output "
            "or pass --overwrite after reviewing it"
        )

    validation = validate_inputs(args.data_dir)
    print(validation.render())
    if not validation.is_valid:
        return 1

    patients = pd.read_csv(args.data_dir / "patients.csv.gz")
    admissions = pd.read_csv(args.data_dir / "admissions.csv.gz")
    diagnoses = pd.read_csv(args.data_dir / "diagnoses_icd.csv.gz")
    diagnosis_dictionary = pd.read_csv(
        args.data_dir / "d_icd_diagnoses.csv.gz"
    )

    cohort, flow = build_cohort(
        patients,
        admissions,
        diagnoses,
        diagnosis_dictionary,
        administrative_end_date=args.administrative_end_date,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cohort.to_csv(output_path, index=False)

    print("\nCohort flow (aggregate counts only):")
    for label, count in flow.items():
        print(f"{label}: {count}")
    print(f"\nSaved cohort to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
