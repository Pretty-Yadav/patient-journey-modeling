from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from lifelines import KaplanMeierFitter


# -----------------------------
# Configuration
# -----------------------------
COHORT_PATH = Path("data/processed/cohort.csv")
OUTPUT_PATH = Path("reports/kaplan_meier_overall.png")


# -----------------------------
# Load cohort
# -----------------------------
print("Loading cohort...")

df = pd.read_csv(COHORT_PATH)

print(f"Patients in cohort: {len(df)}")


# -----------------------------
# Prepare survival data
# -----------------------------
# time_to_event_days = time from
# index discharge to first event/censoring
#
# event = 0 -> censored
# event = 1 -> readmission
# event = 2 -> death
#
# For this first Kaplan-Meier analysis,
# we treat both readmission and death
# as an event.

df["overall_event"] = (df["event"] > 0).astype(int)


# -----------------------------
# Fit Kaplan-Meier model
# -----------------------------
kmf = KaplanMeierFitter()

kmf.fit(
    durations=df["time_to_event_days"],
    event_observed=df["overall_event"],
    label="Any event"
)


# -----------------------------
# Print survival estimates
# -----------------------------
print()
print("========================================")
print("KAPLAN-MEIER ANALYSIS")
print("========================================")

print(f"Number of patients: {len(df)}")
print(f"Number of events: {df['overall_event'].sum()}")
print(f"Number censored: {(df['overall_event'] == 0).sum()}")

print()
print("Survival probability at selected time points:")

for day in [30, 90, 180]:
    survival_probability = kmf.predict(day)
    print(
        f"{day} days: "
        f"{survival_probability:.3f}"
    )


# -----------------------------
# Create survival curve
# -----------------------------
OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)

plt.figure(figsize=(10, 6))

kmf.plot_survival_function()

plt.title(
    "Kaplan-Meier Curve: Time to First Event"
)

plt.xlabel("Days after index discharge")

plt.ylabel("Probability of remaining event-free")

plt.xlim(0, 180)
plt.ylim(0, 1.05)

plt.grid(True, alpha=0.3)

plt.tight_layout()

plt.savefig(
    OUTPUT_PATH,
    dpi=300
)

plt.show()

print()
print("Kaplan-Meier curve saved to:")
print(OUTPUT_PATH)
