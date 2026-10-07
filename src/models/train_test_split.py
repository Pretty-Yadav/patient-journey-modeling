from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split


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

X = df[
    [
        "anchor_age",
        "gender",
    ]
]

y = df["readmission_180d"]


# ==============================
# Stratified train/test split
# ==============================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.25,
    random_state=RANDOM_SEED,
    stratify=y,
)


# ==============================
# Rebuild datasets
# ==============================

train_df = X_train.copy()
train_df["readmission_180d"] = y_train

test_df = X_test.copy()
test_df["readmission_180d"] = y_test


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
print(train_df["readmission_180d"].value_counts())

print()
print("Testing target distribution:")
print(test_df["readmission_180d"].value_counts())

print()
print("Saved:")
print(TRAIN_PATH)
print(TEST_PATH)
