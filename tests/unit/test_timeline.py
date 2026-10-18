import unittest

import pandas as pd

from src.timeline.build_enriched_timeline import build_enriched_timeline
from src.timeline.create_observation_window import create_observation_window


class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.admissions = pd.DataFrame(
            [
                (1, 10, "2200-01-01", "2200-01-03", "URGENT", "HOME"),
                (1, 11, "2200-01-10", "2200-01-12", "EMERGENCY", "HOME"),
                (2, 20, "2200-01-01", "2200-01-03", "URGENT", "HOME"),
            ],
            columns=[
                "subject_id",
                "hadm_id",
                "admittime",
                "dischtime",
                "admission_type",
                "discharge_location",
            ],
        )
        self.diagnoses = pd.DataFrame(
            [
                (1, 10, "A00", 10),
                (1, 11, "B00", 10),
                (2, 20, "A00", 10),
            ],
            columns=["subject_id", "hadm_id", "icd_code", "icd_version"],
        )
        self.dictionary = pd.DataFrame(
            [
                ("A00", 10, "Diagnosis A"),
                ("B00", 10, "Diagnosis B"),
            ],
            columns=["icd_code", "icd_version", "long_title"],
        )
        self.cohort = pd.DataFrame(
            [
                (
                    1,
                    10,
                    "2199-12-30",
                    "2200-01-03",
                    1,
                    "2200-01-10",
                    "2200-02-01",
                ),
                (
                    2,
                    20,
                    "2199-12-30",
                    "2200-01-03",
                    2,
                    "2200-01-20",
                    "2200-02-01",
                ),
                (
                    3,
                    30,
                    "2199-12-30",
                    "2200-01-03",
                    0,
                    None,
                    "2200-01-20",
                ),
            ],
            columns=[
                "subject_id",
                "index_hadm_id",
                "index_admittime",
                "index_dischtime",
                "event",
                "event_date",
                "followup_end_date",
            ],
        )

    def test_enriched_timeline_has_stable_order_and_encounter_diagnoses(self):
        timeline = build_enriched_timeline(
            self.admissions, self.diagnoses, self.dictionary, self.cohort
        )

        self.assertEqual(
            timeline.event_type.value_counts().to_dict(),
            {
                "diagnosis": 3,
                "hospital_admission": 3,
                "hospital_discharge": 3,
            },
        )
        same_time = timeline.loc[
            timeline.subject_id.eq(1)
            & timeline.event_time.eq(pd.Timestamp("2200-01-01"))
        ]
        self.assertEqual(
            same_time.event_type.tolist(),
            ["hospital_admission", "diagnosis"],
        )
        diagnosis = timeline.loc[timeline.event_type.eq("diagnosis")].iloc[0]
        self.assertEqual(diagnosis.event_time, pd.Timestamp("2200-01-01"))
        self.assertEqual(diagnosis.event_description, "Diagnosis A")

    def test_journey_stops_at_competing_event_or_censoring(self):
        timeline = build_enriched_timeline(
            self.admissions, self.diagnoses, self.dictionary, self.cohort
        )
        journey = create_observation_window(timeline, self.cohort)

        patient_one = journey.loc[journey.subject_id.eq(1)]
        self.assertEqual(
            patient_one.event_time.max(), pd.Timestamp("2200-01-10")
        )
        readmission = patient_one.loc[patient_one.is_first_event]
        self.assertEqual(len(readmission), 1)
        self.assertEqual(readmission.iloc[0].event_type, "hospital_admission")
        self.assertTrue(
            patient_one.event_time.le(pd.Timestamp("2200-01-10")).all()
        )

        patient_two = journey.loc[journey.subject_id.eq(2)]
        death = patient_two.loc[patient_two.event_type.eq("death")]
        self.assertEqual(len(death), 1)
        self.assertTrue(death.iloc[0].is_first_event)
        self.assertEqual(death.iloc[0].days_from_index, 17)

        patient_three = journey.loc[journey.subject_id.eq(3)]
        self.assertTrue(patient_three.event_time.le(pd.Timestamp("2200-01-20")).all())
        self.assertFalse(patient_three.is_first_event.any())

    def test_rejects_missing_followup_end_and_inconsistent_event(self):
        timeline = build_enriched_timeline(
            self.admissions, self.diagnoses, self.dictionary, self.cohort
        )
        with self.assertRaisesRegex(ValueError, "followup_end_date"):
            create_observation_window(
                timeline, self.cohort.drop(columns="followup_end_date")
            )

        bad_cohort = self.cohort.copy()
        bad_cohort.loc[0, "event_date"] = "2200-01-08"
        with self.assertRaisesRegex(ValueError, "no matching hospital_admission"):
            create_observation_window(timeline, bad_cohort)


if __name__ == "__main__":
    unittest.main()
