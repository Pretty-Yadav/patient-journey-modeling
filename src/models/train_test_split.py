from pathlib import Path

import pandas as pd

from src.models.split_validation import create_patient_level_split


# ==============================
# Configuration
# ==============================

INPUT_PATH = Path("data/processed/ml_baseline.csv")

TRAIN_PATH = Path("data/processed/train.csv")
TEST_PATH = Path("data/processed/test.csv")

RANDOM_SEED = 42


# ==============================
# Load data
# ==============================

print("Loading ML dataset...")

df = pd.read_csv(INPUT_PATH)

print(f"Total patients: {len(df)}")


# ==============================
# Define features and target
# ==============================

FEATURES = ["anchor_age", "gender"]
TARGET = "readmission_180d"

train_df, test_df = create_patient_level_split(
    df,
    feature_columns=FEATURES,
    target_column=TARGET,
    test_size=0.25,
    random_seed=RANDOM_SEED,
)


# ==============================
# Save datasets
# ==============================

TRAIN_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)

train_df.to_csv(TRAIN_PATH, index=False)
test_df.to_csv(TEST_PATH, index=False)


# ==============================
# Display results
# ==============================

print()
print("========================================")
print("TRAIN / TEST SPLIT")
print("========================================")

print(f"Training patients: {len(train_df)}")
print(f"Testing patients:  {len(test_df)}")

print()
print("Training target distribution:")
print(train_df[TARGET].value_counts())

print()
print("Testing target distribution:")
print(test_df[TARGET].value_counts())

print()
print("Saved:")
print(TRAIN_PATH)
print(TEST_PATH)
