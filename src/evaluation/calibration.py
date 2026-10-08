import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import brier_score_loss
from sklearn.calibration import calibration_curve


# Load XGBoost predictions
predictions = pd.read_csv(
    "data/processed/xgboost_predictions.csv"
)

# Actual outcome
y_true = predictions["readmission_180d"]

# Predicted probability
y_prob = predictions["predicted_probability"]


# Calculate Brier Score
brier = brier_score_loss(y_true, y_prob)

print("=" * 40)
print("XGBOOST PROBABILITY CALIBRATION")
print("=" * 40)

print(f"Number of patients: {len(predictions)}")
print(f"Number of readmissions: {y_true.sum()}")
print(f"Brier Score: {brier:.4f}")


# Calculate calibration curve
prob_true, prob_pred = calibration_curve(
    y_true,
    y_prob,
    n_bins=3,
    strategy="uniform"
)


# Create calibration plot
plt.figure(figsize=(7, 6))

plt.plot(
    prob_pred,
    prob_true,
    marker="o",
    label="XGBoost"
)

plt.plot(
    [0, 1],
    [0, 1],
    linestyle="--",
    label="Perfect Calibration"
)

plt.xlabel("Mean Predicted Probability")
plt.ylabel("Observed Readmission Rate")
plt.title("XGBoost Calibration Curve - 180 Day Readmission")

plt.legend()
plt.grid(True)

plt.tight_layout()

plt.savefig(
    "reports/xgboost_calibration.png",
    dpi=300
)

print()
print("Calibration curve saved to:")
print("reports/xgboost_calibration.png")
