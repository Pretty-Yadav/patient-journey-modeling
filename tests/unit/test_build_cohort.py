import unittest

import pandas as pd

from src.cohort.build_cohort import build_cohort


class BuildCohortTests(unittest.TestCase):
    def setUp(self):
        self.patients = pd.DataFrame(
            [
                (1, "F", 60, "2200-03-01"),
                (2, "M", 70, "2200-02-05"),
                (3, "F", 55, None),
                (4, "M", 65, "2200-01-02"),
            ],
            columns=["subject_id", "gender", "anchor_age", "dod"],
        )
        self.admissions = pd.DataFrame(
            [
                (1, 10, "2200-01-01", "2200-01-03", 0),
                (1, 11, "2200-01-10", "2200-01-12", 0),
                (1, 12, "2200-01-20 10:00", "2200-01-21", 0),
                (2, 20, "2200-01-01", "2200-01-03", 0),
                (2, 21, "2200-02-05 12:00", "2200-02-06", 0),
                (3, 30, "2200-01-01", "2200-01-03", 0),
                (3, 31, "2200-07-10", "2200-07-11", 0),
                (4, 40, "2200-01-01", "2200-01-03", 1),
            ],
            columns=[
                "subject_id",
                "hadm_id",
                "admittime",
                "dischtime",
                "hospital_expire_flag",
            ],
        )
        self.diagnoses = pd.DataFrame(
            [
                (1, 10, "NON-HF", 10),
                (1, 11, "HF", 10),
                (2, 20, "HF", 10),
                (3, 30, "HF", 10),
                (4, 40, "HF", 10),
            ],
            columns=["subject_id", "hadm_id", "icd_code", "icd_version"],
        )
        self.dictionary = pd.DataFrame(
            [
                ("HF", 10, "Acute heart failure"),
                ("NON-HF", 10, "Condition without heart failure"),
            ],
            columns=["icd_code", "icd_version", "long_title"],
        )

    def build(self, end_date="2200-03-31", max_followup_days=180):
        return build_cohort(
            self.patients,
            self.admissions,
            self.diagnoses,
            self.dictionary,
            administrative_end_date=end_date,
            max_followup_days=max_followup_days,
        )

    def test_uses_first_heart_failure_admission_and_one_row_per_patient(self):
        cohort, flow = self.build()

        self.assertEqual(cohort["subject_id"].tolist(), [1, 2, 3])
        self.assertEqual(cohort["subject_id"].nunique(), len(cohort))
        patient_one = cohort.set_index("subject_id").loc[1]
        self.assertEqual(patient_one["index_hadm_id"], 11)
        self.assertEqual(patient_one["event"], 1)
        self.assertEqual(patient_one["event_label"], "readmission")
        self.assertEqual(patient_one["readmission_date"], pd.Timestamp("2200-01-20 10:00"))
        self.assertEqual(flow["excluded_death_during_or_on_index_discharge"], 1)

    def test_death_is_competing_event_and_censoring_ends_at_cutoff(self):
        cohort, _ = self.build()
        rows = cohort.set_index("subject_id")

        self.assertEqual(rows.loc[2, "event"], 2)
        self.assertEqual(rows.loc[2, "event_label"], "death")
        self.assertEqual(rows.loc[2, "event_date"], pd.Timestamp("2200-02-05"))
        self.assertEqual(rows.loc[2, "time_to_event_days"], 33)
        self.assertEqual(rows.loc[3, "event"], 0)
        self.assertEqual(rows.loc[3, "event_label"], "censored")
        self.assertLess(rows.loc[3, "time_to_event_days"], 180)
        self.assertEqual(
            rows.loc[3, "followup_end_date"],
            pd.Timestamp("2200-03-31 23:59:59.999999999"),
        )
        self.assertTrue(pd.isna(rows.loc[3, "event_date"]))

    def test_followup_is_capped_at_180_days_and_later_events_do_not_count(self):
        cohort, _ = self.build(end_date="2210-01-01")
        patient_three = cohort.set_index("subject_id").loc[3]

        expected_end = patient_three["index_dischtime"] + pd.Timedelta(
            180, unit="D"
        )
        self.assertEqual(patient_three["event"], 0)
        self.assertEqual(patient_three["time_to_event_days"], 180)
        self.assertEqual(patient_three["followup_end_date"], expected_end)
        self.assertTrue(pd.isna(patient_three["readmission_date"]))

    def test_rejects_administrative_end_before_index_discharge(self):
        with self.assertRaisesRegex(ValueError, "precedes one or more index discharges"):
            self.build(end_date="2199-12-31")

    def test_rejects_duplicate_patient_keys(self):
        patients = pd.concat([self.patients, self.patients.iloc[[0]]])

        with self.assertRaisesRegex(ValueError, "duplicate keys: subject_id"):
            build_cohort(
                patients,
                self.admissions,
                self.diagnoses,
                self.dictionary,
                administrative_end_date="2200-03-31",
            )


if __name__ == "__main__":
    unittest.main()
