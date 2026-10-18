import gzip
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.data.validate_inputs import validate_inputs


class ValidateInputsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self._write_tables()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_table(self, filename, rows):
        path = self.data_dir / filename
        pd.DataFrame(rows).to_csv(path, index=False, compression="gzip")

    def _write_tables(self):
        self._write_table(
            "patients.csv.gz",
            [{"subject_id": 1, "gender": "F", "anchor_age": 60, "dod": None}],
        )
        self._write_table(
            "admissions.csv.gz",
            [
                {
                    "subject_id": 1,
                    "hadm_id": 10,
                    "admittime": "2100-01-01",
                    "dischtime": "2100-01-03",
                    "hospital_expire_flag": 0,
                }
            ],
        )
        self._write_table(
            "diagnoses_icd.csv.gz",
            [
                {
                    "subject_id": 1,
                    "hadm_id": 10,
                    "seq_num": 1,
                    "icd_code": "A00",
                    "icd_version": 10,
                }
            ],
        )
        self._write_table(
            "d_icd_diagnoses.csv.gz",
            [{"icd_code": "A00", "icd_version": 10, "long_title": "Example"}],
        )

    def test_valid_inputs_pass(self):
        report = validate_inputs(self.data_dir)

        self.assertTrue(report.is_valid, report.render())
        self.assertEqual(len(report.files), 4)

    def test_missing_file_is_reported(self):
        (self.data_dir / "patients.csv.gz").unlink()

        report = validate_inputs(self.data_dir)

        self.assertFalse(report.is_valid)
        self.assertIn(
            "Required input is missing: patients.csv.gz", report.issues
        )

    def test_invalid_dates_and_duplicate_keys_are_reported(self):
        self._write_table(
            "admissions.csv.gz",
            [
                {
                    "subject_id": 1,
                    "hadm_id": 10,
                    "admittime": "not-a-date",
                    "dischtime": "2100-01-03",
                    "hospital_expire_flag": 0,
                },
                {
                    "subject_id": 1,
                    "hadm_id": 10,
                    "admittime": "2100-01-01",
                    "dischtime": "2099-12-31",
                    "hospital_expire_flag": 0,
                },
            ],
        )

        report = validate_inputs(self.data_dir)
        rendered = report.render()

        self.assertFalse(report.is_valid)
        self.assertIn("duplicate key: hadm_id", rendered)
        self.assertIn("missing or invalid admittime", rendered)
        self.assertIn("discharges before admissions", rendered)

    def test_missing_required_column_is_reported(self):
        self._write_table(
            "d_icd_diagnoses.csv.gz",
            [{"icd_code": "A00", "icd_version": 10}],
        )

        report = validate_inputs(self.data_dir)

        self.assertFalse(report.is_valid)
        self.assertIn(
            "d_icd_diagnoses.csv.gz is missing required columns: long_title",
            report.issues,
        )


if __name__ == "__main__":
    unittest.main()
