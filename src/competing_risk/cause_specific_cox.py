from pathlib import Path

import pandas as pd
from lifelines import CoxPHFitter


# ==============================
# Configuration
# ==============================

COHORT_PATH = Path("data/processed/cohort.csv")


# ==============================
# Load cohort
# ==============================

print("Loading cohort...")

df = pd.read_csv(COHORT_PATH)

print(f"Patients in cohort: {len(df)}")


# ==============================
# Create cause-specific event
# ==============================

# For the readmission model:
#
# 1 = readmission
# 0 = everything else
#
# Death is treated as a competing event
# and therefore censored for this model.

df["readmission_event"] = (df["event"] == 1).astype(int)


# ==============================
# Select model variables
# ==============================

model_df = df[
    [
        "time_to_event_days",
        "readmission_event",
        "anchor_age",
        "gender",
    ]
].copy()


# ==============================
# Convert gender to numeric
# ==============================

model_df["gender"] = model_df["gender"].map(
    {
        "M": 0,
        "F": 1,
    }
)


# Remove rows with missing values
model_df = model_df.dropna()


print()
print("Data used for model:")
print(model_df.head())

print()
print(f"Rows used: {len(model_df)}")
print(f"Readmission events: {model_df['readmission_event'].sum()}")


# ==============================
# Fit Cause-Specific Cox model
# ==============================

print()
print("Fitting cause-specific Cox model...")

cph = CoxPHFitter()

cph.fit(
    model_df,
    duration_col="time_to_event_days",
    event_col="readmission_event",
)


# ==============================
# Display results
# ==============================

print()
print("========================================")
print("CAUSE-SPECIFIC COX MODEL")
print("Outcome: Readmission")
print("========================================")

cph.print_summary()
