import unittest

import pandas as pd

from src.models.split_validation import create_patient_level_split


class PatientLevelSplitTests(unittest.TestCase):
    def setUp(self):
        self.dataset = pd.DataFrame(
            {
                "subject_id": range(100, 112),
                "anchor_age": range(50, 62),
                "gender": [0, 1] * 6,
                "readmission_180d": [0, 1] * 6,
            }
        )

    def test_split_is_reproducible_and_patient_ids_do_not_overlap(self):
        first_train, first_test = create_patient_level_split(
            self.dataset,
            feature_columns=["anchor_age", "gender"],
            target_column="readmission_180d",
        )
        second_train, second_test = create_patient_level_split(
            self.dataset,
            feature_columns=["anchor_age", "gender"],
            target_column="readmission_180d",
        )

        pd.testing.assert_frame_equal(first_train, second_train)
        pd.testing.assert_frame_equal(first_test, second_test)
        self.assertTrue(set(first_train["subject_id"]).isdisjoint(first_test["subject_id"]))
        self.assertEqual(
            set(first_train["subject_id"]) | set(first_test["subject_id"]),
            set(self.dataset["subject_id"]),
        )
        self.assertIn("subject_id", first_train.columns)

    def test_rejects_duplicate_patient_rows(self):
        duplicate = pd.concat([self.dataset, self.dataset.iloc[[0]]], ignore_index=True)

        with self.assertRaisesRegex(ValueError, "exactly one"):
            create_patient_level_split(
                duplicate,
                feature_columns=["anchor_age", "gender"],
                target_column="readmission_180d",
            )

    def test_rejects_target_without_two_examples_per_class(self):
        insufficient_class = self.dataset.copy()
        insufficient_class["readmission_180d"] = [1] + [0] * 11

        with self.assertRaisesRegex(ValueError, "at least two patients"):
            create_patient_level_split(
                insufficient_class,
                feature_columns=["anchor_age", "gender"],
                target_column="readmission_180d",
            )


if __name__ == "__main__":
    unittest.main()