from pathlib import Path

import pandas as pd

from xgboost import XGBClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


# ==============================
# Configuration
# ==============================

TRAIN_PATH = Path("data/processed/train.csv")
TEST_PATH = Path("data/processed/test.csv")

PREDICTION_PATH = Path(
    "data/processed/xgboost_predictions.csv"
)


# ==============================
# Load data
# ==============================

print("Loading training and testing data...")

train_df = pd.read_csv(TRAIN_PATH)
test_df = pd.read_csv(TEST_PATH)


FEATURES = [
    "anchor_age",
    "gender",
]

TARGET = "readmission_180d"


X_train = train_df[FEATURES]
y_train = train_df[TARGET]

X_test = test_df[FEATURES]
y_test = test_df[TARGET]


print()
print(f"Training patients: {len(X_train)}")
print(f"Testing patients: {len(X_test)}")


# ==============================
# Calculate class imbalance
# ==============================

negative_cases = (y_train == 0).sum()
positive_cases = (y_train == 1).sum()

scale_pos_weight = (
    negative_cases / positive_cases
)


print()
print("Training class distribution:")
print(f"Non-readmission: {negative_cases}")
print(f"Readmission:     {positive_cases}")
print(
    f"Scale positive weight: "
    f"{scale_pos_weight:.2f}"
)


# ==============================
# Create XGBoost model
# ==============================

model = XGBClassifier(
    n_estimators=100,
    max_depth=3,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=scale_pos_weight,
    random_state=42,
    eval_metric="logloss",
)


# ==============================
# Train
# ==============================

print()
print("Training XGBoost model...")

model.fit(
    X_train,
    y_train,
)


# ==============================
# Predictions
# ==============================

y_pred = model.predict(X_test)

y_probability = model.predict_proba(
    X_test
)[:, 1]


# ==============================
# Evaluation
# ==============================

accuracy = accuracy_score(
    y_test,
    y_pred,
)

precision = precision_score(
    y_test,
    y_pred,
    zero_division=0,
)

recall = recall_score(
    y_test,
    y_pred,
    zero_division=0,
)


if y_test.nunique() == 2:

    roc_auc = roc_auc_score(
        y_test,
        y_probability,
    )

else:

    roc_auc = None


# ==============================
# Print results
# ==============================

print()
print("========================================")
print("XGBOOST BASELINE - CLASS IMBALANCE")
print("========================================")

print(f"Accuracy:  {accuracy:.3f}")
print(f"Precision: {precision:.3f}")
print(f"Recall:    {recall:.3f}")

if roc_auc is not None:
    print(f"ROC-AUC:   {roc_auc:.3f}")
else:
    print("ROC-AUC:   Cannot calculate")


# ==============================
# Save predictions
# ==============================

results = test_df[
    [
        "anchor_age",
        "gender",
        "readmission_180d",
    ]
].copy()

results["predicted_probability"] = (
    y_probability
)

results["predicted_class"] = y_pred


PREDICTION_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)

results.to_csv(
    PREDICTION_PATH,
    index=False
)


print()
print("Predictions:")
print(
    results.to_string(index=False)
)

print()
print("Predictions saved to:")
print(PREDICTION_PATH)
