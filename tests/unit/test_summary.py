import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from api.routes import summary


class SummaryTests(unittest.TestCase):
    def test_uses_tracked_cohort_when_phase3_artifact_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cohort_path = Path(temp_dir) / "cohort.csv"
            pd.DataFrame({"event": [0, 0, 1, 2]}).to_csv(cohort_path, index=False)

            with (
                patch.object(summary, "COHORT_PATH", Path(temp_dir) / "missing.csv"),
                patch.object(summary, "FALLBACK_COHORT_PATH", cohort_path),
                patch.object(summary, "PREDICTIONS_PATH", Path(temp_dir) / "predictions.csv"),
                patch.object(summary, "FEATURE_IMPORTANCE_PATH", Path(temp_dir) / "importance.csv"),
                patch.object(summary, "SUBGROUP_PATH", Path(temp_dir) / "subgroups.csv"),
            ):
                result = summary.get_summary()

        self.assertEqual(
            result["cohort"],
            {"rows": 4, "readmission_events": 1, "death_events": 1, "censored": 2},
        )


if __name__ == "__main__":
    unittest.main()