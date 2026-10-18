import unittest

import pandas as pd

from src.competing_risk.cumulative_incidence import (
    compute_cumulative_incidence,
    prepare_competing_risk_data,
)


class CompetingRiskTests(unittest.TestCase):
    def test_prepare_competing_risk_data_keeps_event_codes(self):
        cohort = pd.DataFrame(
            {
                "subject_id": [1, 2, 3],
                "time_to_event_days": [10.0, 20.0, 30.0],
                "event": [1, 2, 0],
            }
        )

        data = prepare_competing_risk_data(cohort)

        self.assertEqual(data["event_code"].tolist(), [1, 2, 0])
        self.assertEqual(data["readmission_indicator"].tolist(), [1, 0, 0])
        self.assertEqual(data["death_indicator"].tolist(), [0, 1, 0])

    def test_compute_cumulative_incidence_matches_known_values(self):
        cohort = pd.DataFrame(
            {
                "subject_id": [1, 2, 3],
                "time_to_event_days": [10.0, 20.0, 30.0],
                "event": [1, 2, 0],
            }
        )

        result = compute_cumulative_incidence(cohort)

        readmission = result.loc[
            (result["time_point"] == 20.0)
            & (result["event_type"] == "readmission"),
            "cumulative_incidence",
        ].iloc[0]
        death = result.loc[
            (result["time_point"] == 20.0)
            & (result["event_type"] == "death"),
            "cumulative_incidence",
        ].iloc[0]

        self.assertAlmostEqual(readmission, 0.3333333333, places=6)
        self.assertAlmostEqual(death, 0.3333333333, places=6)


if __name__ == "__main__":
    unittest.main()
