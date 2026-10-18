from pathlib import Path

import pandas as pd


# ==============================
# Configuration
# ==============================

COHORT_PATH = Path("data/processed/cohort.csv")
OUTPUT_PATH = Path("data/processed/ml_baseline.csv")


# ==============================
# Load cohort
# ==============================

print("Loading cohort...")

df = pd.read_csv(COHORT_PATH)

print(f"Original patients: {len(df)}")


# ==============================
# Create ML target
# ==============================

# Target:
# 1 = readmission occurred within 180 days
# 0 = no readmission within 180 days
#
# Death is NOT treated as readmission.

df["readmission_180d"] = (
    df["event"] == 1
).astype(int)


# ==============================
# Select predictors
# ==============================

ml_df = df[
    [
        "subject_id",
        "anchor_age",
        "gender",
        "readmission_180d",
    ]
].copy()


# ==============================
# Encode gender
# ==============================

ml_df["gender"] = ml_df["gender"].map(
    {
        "M": 0,
        "F": 1,
    }
)


# ==============================
# Remove missing values
# ==============================

ml_df = ml_df.dropna()


# ==============================
# Save dataset
# ==============================

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)

ml_df.to_csv(
    OUTPUT_PATH,
    index=False
)


# ==============================
# Summary
# ==============================

print()
print("========================================")
print("ML DATASET CREATED")
print("========================================")

print(f"Patients used: {len(ml_df)}")

print()
print("Features:")
print("  - anchor_age")
print("  - gender")

print()
print("Target:")
print("  - readmission_180d")

print()
print("Target distribution:")
print(
    ml_df["readmission_180d"]
    .value_counts()
    .sort_index()
)

print()
print("First 10 rows:")
print(ml_df.head(10).to_string(index=False))

print()
print("Saved to:")
print(OUTPUT_PATH)
