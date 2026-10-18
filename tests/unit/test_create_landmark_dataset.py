import unittest

import pandas as pd

from src.timeline.create_landmark_dataset import create_landmark_dataset


class CreateLandmarkDatasetTests(unittest.TestCase):
    def test_uses_patient_specific_followup_end_date_for_censored_label(self):
        cohort = pd.DataFrame(
            [
                (1, 101, pd.Timestamp("2020-01-01"), 70, "F", 1, "readmission", 60, pd.Timestamp("2020-03-01")),
                (2, 102, pd.Timestamp("2020-01-10"), 65, "M", 2, "death", 120, pd.Timestamp("2020-04-15")),
                (3, 103, pd.Timestamp("2020-02-01"), 80, "F", 0, "censored", 90, pd.Timestamp("2020-04-30")),
            ],
            columns=[
                "subject_id",
                "index_hadm_id",
                "index_dischtime",
                "anchor_age",
                "gender",
                "event",
                "event_label",
                "time_to_event_days",
                "followup_end_date",
            ],
        )
        timeline = pd.DataFrame(
            [
                (1, "diagnosis", "diagnosis before landmark", 20),
                (2, "diagnosis", "diagnosis before landmark", 10),
                (2, "diagnosis", "diagnosis after landmark", 40),
                (3, "diagnosis", "diagnosis before landmark", 15),
            ],
            columns=[
                "subject_id",
                "event_type",
                "event_description",
                "days_from_index",
            ],
        )

        dataset = create_landmark_dataset(
            cohort,
            timeline,
            landmark_days=(30,),
            followup_end_day=180,
        ).set_index("subject_id")

        self.assertEqual(dataset.loc[3, "event_after_landmark_label"], "no_event_by_day_89")
        self.assertEqual(dataset.loc[1, "event_after_landmark_label"], "readmission")
        self.assertEqual(dataset.loc[2, "event_after_landmark_label"], "death")

    def test_excludes_prior_events_and_uses_past_history(self):
        cohort = pd.DataFrame(
            [
                (1, 101, pd.Timestamp("2020-01-01"), 70, "F", 1, "readmission", 60, pd.Timestamp("2020-03-01")),
                (2, 102, pd.Timestamp("2020-01-10"), 65, "M", 2, "death", 120, pd.Timestamp("2020-04-15")),
                (3, 103, pd.Timestamp("2020-02-01"), 80, "F", 0, "censored", 180, pd.Timestamp("2020-05-31")),
                (4, 104, pd.Timestamp("2020-03-01"), 50, "M", 1, "readmission", 30, pd.Timestamp("2020-03-31")),
            ],
            columns=[
                "subject_id",
                "index_hadm_id",
                "index_dischtime",
                "anchor_age",
                "gender",
                "event",
                "event_label",
                "time_to_event_days",
                "followup_end_date",
            ],
        )
        timeline = pd.DataFrame(
            [
                (1, "hospital_discharge", "home", 0),
                (1, "diagnosis", "diagnosis before landmark", 20),
                (1, "hospital_admission", "readmission", 60),
                (2, "diagnosis", "diagnosis before landmark", 10),
                (2, "diagnosis", "diagnosis after landmark", 40),
                (3, "diagnosis", "diagnosis before landmark", 15),
                (4, "hospital_admission", "readmission", 30),
            ],
            columns=[
                "subject_id",
                "event_type",
                "event_description",
                "days_from_index",
            ],
        )

        dataset = create_landmark_dataset(
            cohort,
            timeline,
            landmark_days=(30,),
            followup_end_day=180,
        ).set_index("subject_id")

        self.assertEqual(dataset.index.tolist(), [1, 2, 3])
        self.assertEqual(dataset.loc[1, "event_after_landmark"], 1)
        self.assertEqual(dataset.loc[2, "event_after_landmark"], 2)
        self.assertEqual(dataset.loc[3, "event_after_landmark"], 0)
        self.assertEqual(dataset.loc[2, "history_diagnosis_count"], 1)
        self.assertEqual(dataset.loc[2, "history_unique_diagnosis_count"], 1)
        self.assertEqual(dataset.loc[1, "time_to_event_after_landmark_days"], 30)