from pathlib import Path

import pandas as pd
from lifelines import CoxPHFitter


COHORT_PATH = Path("data/processed/cohort.csv")


print("Loading cohort...")

df = pd.read_csv(COHORT_PATH)

print(f"Patients in cohort: {len(df)}")


# Death is the event of interest
# Readmission is treated as a competing event

df["death_event"] = (df["event"] == 2).astype(int)


model_df = df[
    [
        "time_to_event_days",
        "death_event",
        "anchor_age",
        "gender",
    ]
].copy()


model_df["gender"] = model_df["gender"].map(
    {
        "M": 0,
        "F": 1,
    }
)


model_df = model_df.dropna()


print()
print(f"Rows used: {len(model_df)}")
print(f"Death events: {model_df['death_event'].sum()}")


print()
print("Fitting cause-specific Cox model for death...")


cph = CoxPHFitter()

cph.fit(
    model_df,
    duration_col="time_to_event_days",
    event_col="death_event",
)


print()
print("========================================")
print("CAUSE-SPECIFIC COX MODEL")
print("Outcome: Death")
print("========================================")

cph.print_summary()
