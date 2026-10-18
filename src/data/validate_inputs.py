"""Validate local MIMIC-IV Demo CSV inputs without printing patient records."""

from __future__ import annotations

import argparse
import gzip
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


DEFAULT_DATA_DIR = (
    Path(__file__).resolve().parents[2]
    / "physionet.org/files/mimic-iv-demo/2.2/hosp"
)

REQUIRED_COLUMNS = {
    "patients.csv.gz": {"subject_id", "gender", "anchor_age", "dod"},
    "admissions.csv.gz": {
        "subject_id",
        "hadm_id",
        "admittime",
        "dischtime",
        "hospital_expire_flag",
    },
    "diagnoses_icd.csv.gz": {
        "subject_id",
        "hadm_id",
        "seq_num",
        "icd_code",
        "icd_version",
    },
    "d_icd_diagnoses.csv.gz": {
        "icd_code",
        "icd_version",
        "long_title",
    },
}


@dataclass
class FileCheck:
    filename: str
    status: str
    rows: int | None = None
    detail: str = ""


@dataclass
class ValidationReport:
    files: list[FileCheck] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.issues

    def render(self) -> str:
        lines = ["MIMIC-IV Demo input validation", ""]
        for check in self.files:
            row_count = f", rows={check.rows}" if check.rows is not None else ""
            detail = f" — {check.detail}" if check.detail else ""
            lines.append(f"{check.filename}: {check.status}{row_count}{detail}")
        lines.append("")
        if self.issues:
            lines.append("Issues:")
            lines.extend(f"- {issue}" for issue in self.issues)
        else:
            lines.append("No validation issues found.")
        return "\n".join(lines)


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, compression="gzip")


def validate_inputs(data_dir: Path = DEFAULT_DATA_DIR) -> ValidationReport:
    """Validate required Demo input files and their basic relational integrity."""
    report = ValidationReport()
    tables: dict[str, pd.DataFrame] = {}

    for filename, required_columns in REQUIRED_COLUMNS.items():
        path = data_dir / filename
        if not path.is_file():
            report.files.append(FileCheck(filename, "MISSING"))
            report.issues.append(f"Required input is missing: {filename}")
            continue

        try:
            table = _read_csv(path)
        except (OSError, EOFError, gzip.BadGzipFile, pd.errors.ParserError,
                pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
            report.files.append(
                FileCheck(filename, "UNREADABLE", detail=type(exc).__name__)
            )
            report.issues.append(f"Could not read {filename} as gzip CSV")
            continue

        missing_columns = required_columns.difference(table.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            report.files.append(
                FileCheck(
                    filename,
                    "INVALID SCHEMA",
                    rows=len(table),
                    detail=f"missing required columns: {missing}",
                )
            )
            report.issues.append(
                f"{filename} is missing required columns: {missing}"
            )
            continue

        tables[filename] = table
        report.files.append(FileCheck(filename, "OK", rows=len(table)))
        if table.empty:
            report.issues.append(f"Required input contains no rows: {filename}")

    patients = tables.get("patients.csv.gz")
    admissions = tables.get("admissions.csv.gz")
    diagnoses = tables.get("diagnoses_icd.csv.gz")
    dictionary = tables.get("d_icd_diagnoses.csv.gz")

    if patients is not None:
        _check_unique_key(
            report, "patients.csv.gz", patients, ["subject_id"]
        )
        missing = int(patients["subject_id"].isna().sum())
        if missing:
            report.issues.append(
                f"patients.csv.gz has {missing} missing subject_id values"
            )
        age = pd.to_numeric(patients["anchor_age"], errors="coerce")
        invalid_age = int((patients["anchor_age"].notna() & age.isna()).sum())
        if invalid_age:
            report.issues.append(
                f"patients.csv.gz has {invalid_age} nonnumeric anchor_age values"
            )
        _check_optional_date(report, "patients.csv.gz", patients, "dod")

    if admissions is not None:
        _check_unique_key(report, "admissions.csv.gz", admissions, ["hadm_id"])
        _check_required_date(report, admissions, "admittime")
        _check_required_date(report, admissions, "dischtime")
        admit = pd.to_datetime(
            admissions["admittime"], format="mixed", errors="coerce"
        )
        discharge = pd.to_datetime(
            admissions["dischtime"], format="mixed", errors="coerce"
        )
        reversed_dates = int((admit.notna() & discharge.notna() & (discharge < admit)).sum())
        if reversed_dates:
            report.issues.append(
                f"admissions.csv.gz has {reversed_dates} discharges before admissions"
            )
        missing_keys = int(
            admissions[["subject_id", "hadm_id"]].isna().any(axis=1).sum()
        )
        if missing_keys:
            report.issues.append(
                f"admissions.csv.gz has {missing_keys} rows missing subject/admission identifiers"
            )

    if diagnoses is not None:
        _check_unique_key(
            report,
            "diagnoses_icd.csv.gz",
            diagnoses,
            ["subject_id", "hadm_id", "seq_num"],
        )
        missing_keys = int(
            diagnoses[
                ["subject_id", "hadm_id", "seq_num", "icd_code", "icd_version"]
            ].isna().any(axis=1).sum()
        )
        if missing_keys:
            report.issues.append(
                f"diagnoses_icd.csv.gz has {missing_keys} rows missing required keys"
            )

    if dictionary is not None:
        _check_unique_key(
            report, "d_icd_diagnoses.csv.gz", dictionary, ["icd_code", "icd_version"]
        )
        missing_keys = int(
            dictionary[["icd_code", "icd_version", "long_title"]]
            .isna()
            .any(axis=1)
            .sum()
        )
        if missing_keys:
            report.issues.append(
                f"d_icd_diagnoses.csv.gz has {missing_keys} rows missing required values"
            )

    if diagnoses is not None and admissions is not None:
        admission_keys = admissions[["subject_id", "hadm_id"]].dropna().drop_duplicates()
        diagnosis_keys = diagnoses[["subject_id", "hadm_id"]].dropna().drop_duplicates()
        linked = diagnosis_keys.merge(
            admission_keys, on=["subject_id", "hadm_id"], how="left", indicator=True
        )
        orphan_count = int((linked["_merge"] == "left_only").sum())
        if orphan_count:
            report.issues.append(
                f"diagnoses_icd.csv.gz has {orphan_count} subject/admission keys "
                "not present in admissions.csv.gz"
            )

    if diagnoses is not None and dictionary is not None:
        code_keys = dictionary[["icd_code", "icd_version"]].dropna().drop_duplicates()
        diagnosis_codes = diagnoses[["icd_code", "icd_version"]].dropna().drop_duplicates()
        linked = diagnosis_codes.merge(
            code_keys, on=["icd_code", "icd_version"], how="left", indicator=True
        )
        unknown_count = int((linked["_merge"] == "left_only").sum())
        if unknown_count:
            report.issues.append(
                f"diagnoses_icd.csv.gz has {unknown_count} distinct codes missing "
                "from d_icd_diagnoses.csv.gz"
            )

    if patients is not None and admissions is not None:
        patient_keys = patients[["subject_id"]].dropna().drop_duplicates()
        admission_subjects = admissions[["subject_id"]].dropna().drop_duplicates()
        linked = admission_subjects.merge(
            patient_keys, on="subject_id", how="left", indicator=True
        )
        orphan_count = int((linked["_merge"] == "left_only").sum())
        if orphan_count:
            report.issues.append(
                f"admissions.csv.gz has {orphan_count} distinct subjects missing "
                "from patients.csv.gz"
            )

    return report


def _check_unique_key(
    report: ValidationReport,
    filename: str,
    table: pd.DataFrame,
    columns: list[str],
) -> None:
    duplicate_rows = int(table.duplicated(columns, keep=False).sum())
    if duplicate_rows:
        key = ", ".join(columns)
        report.issues.append(
            f"{filename} has {duplicate_rows} rows with duplicate key: {key}"
        )


def _check_required_date(
    report: ValidationReport, table: pd.DataFrame, column: str
) -> None:
    parsed = pd.to_datetime(table[column], format="mixed", errors="coerce")
    invalid_count = int(parsed.isna().sum())
    if invalid_count:
        report.issues.append(
            f"admissions.csv.gz has {invalid_count} missing or invalid {column} values"
        )


def _check_optional_date(
    report: ValidationReport,
    filename: str,
    table: pd.DataFrame,
    column: str,
) -> None:
    values = table[column]
    parsed = pd.to_datetime(values, format="mixed", errors="coerce")
    invalid_count = int((values.notna() & parsed.isna()).sum())
    if invalid_count:
        report.issues.append(
            f"{filename} has {invalid_count} invalid {column} values"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate local MIMIC-IV Demo gzip CSV input files."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing the four required MIMIC-IV Demo files.",
    )
    args = parser.parse_args()
    report = validate_inputs(args.data_dir)
    print(report.render())
    return 0 if report.is_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
