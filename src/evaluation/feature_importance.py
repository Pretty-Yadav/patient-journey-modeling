from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from xgboost import XGBClassifier

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TRAIN_PATH = REPOSITORY_ROOT / "data/processed/train.csv"
IMPORTANCE_PATH = REPOSITORY_ROOT / "reports/xgboost_feature_importance.csv"
PLOT_PATH = REPOSITORY_ROOT / "reports/xgboost_feature_importance.png"
FEATURES = ["anchor_age", "gender"]
TARGET = "readmission_180d"


def compute_feature_importance(
    model: XGBClassifier,
    feature_names: list[str],
) -> pd.DataFrame:
    """Return a ranked feature-importance table for an XGBoost model."""
    importances = pd.Series(model.feature_importances_, index=feature_names, dtype=float)
    result = importances.reset_index()
    result.columns = ["feature", "importance"]
    result["importance"] = result["importance"].astype(float)
    result = result.sort_values(
        ["importance", "feature"],
        ascending=[False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    result["rank"] = range(1, len(result) + 1)
    return result[["feature", "importance", "rank"]]


def plot_feature_importance(importance: pd.DataFrame, output_path: Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(7, 5))
    plt.bar(
        importance["feature"],
        importance["importance"],
        color="steelblue",
    )
    plt.ylabel("Feature importance")
    plt.title("XGBoost feature importance for 180-day readmission")
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    return output_path


def main() -> int:
    train_df = pd.read_csv(TRAIN_PATH)
    model = XGBClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=(train_df[TARGET].eq(0).sum() / train_df[TARGET].eq(1).sum()),
        random_state=42,
        eval_metric="logloss",
    )
    model.fit(train_df[FEATURES], train_df[TARGET])

    importance = compute_feature_importance(model, FEATURES)
    IMPORTANCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    importance.to_csv(IMPORTANCE_PATH, index=False)
    plot_feature_importance(importance, PLOT_PATH)

    print("=" * 60)
    print("XGBOOST FEATURE IMPORTANCE")
    print("=" * 60)
    print(importance.to_string(index=False))
    print()
    print(f"Saved importance table to: {IMPORTANCE_PATH}")
    print(f"Saved figure to: {PLOT_PATH}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
