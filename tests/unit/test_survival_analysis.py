import unittest

import pandas as pd

from src.survival.kaplan_meier import fit_kaplan_meier, prepare_survival_data


class SurvivalAnalysisTests(unittest.TestCase):
    def test_prepare_survival_data_marks_any_event(self):
        cohort = pd.DataFrame(
            {
                "subject_id": [1, 2, 3, 4],
                "time_to_event_days": [10.0, 30.0, 45.0, 60.0],
                "event": [0, 1, 2, 0],
            }
        )

        data = prepare_survival_data(cohort)

        self.assertEqual(data["overall_event"].tolist(), [0, 1, 1, 0])
        self.assertEqual(data["time_to_event_days"].tolist(), [10.0, 30.0, 45.0, 60.0])

    def test_fit_kaplan_meier_matches_known_expectation(self):
        cohort = pd.DataFrame(
            {
                "subject_id": [10, 11, 12, 13],
                "time_to_event_days": [30.0, 60.0, 120.0, 180.0],
                "event": [1, 1, 0, 0],
            }
        )

        kmf = fit_kaplan_meier(cohort)

        self.assertAlmostEqual(kmf.predict(30), 0.75, places=6)
        self.assertAlmostEqual(kmf.predict(60), 0.5, places=6)
        self.assertAlmostEqual(kmf.predict(180), 0.5, places=6)

    def test_missing_required_fields_raise_value_error(self):
        cohort = pd.DataFrame({"subject_id": [1, 2], "event": [0, 1]})

        with self.assertRaisesRegex(ValueError, "time_to_event_days"):
            prepare_survival_data(cohort)


if __name__ == "__main__":
    unittest.main()
