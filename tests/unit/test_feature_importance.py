import unittest

import pandas as pd
from xgboost import XGBClassifier

from src.evaluation.feature_importance import compute_feature_importance


class FeatureImportanceTests(unittest.TestCase):
    def test_compute_feature_importance_returns_ranked_table(self):
        df = pd.DataFrame(
            {
                "anchor_age": [60, 65, 70, 75, 80, 85, 90, 95],
                "gender": [0, 1, 0, 1, 0, 1, 0, 1],
                "readmission_180d": [0, 0, 1, 1, 0, 0, 1, 1],
            }
        )

        model = XGBClassifier(
            n_estimators=20,
            max_depth=2,
            learning_rate=0.3,
            random_state=42,
            eval_metric="logloss",
        )
        model.fit(df[["anchor_age", "gender"]], df["readmission_180d"])

        importance = compute_feature_importance(model, ["anchor_age", "gender"])

        self.assertListEqual(list(importance.columns), ["feature", "importance", "rank"])
        self.assertEqual(len(importance), 2)
        self.assertTrue((importance["importance"] >= 0).all())
        self.assertEqual(importance["rank"].tolist(), [1, 2])
        self.assertIn("anchor_age", importance["feature"].tolist())
        self.assertIn("gender", importance["feature"].tolist())


if __name__ == "__main__":
    unittest.main()
