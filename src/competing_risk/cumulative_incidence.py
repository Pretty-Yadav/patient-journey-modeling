from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from sksurv.nonparametric import cumulative_incidence_competing_risks


COHORT_PATH = Path("data/processed/cohort.csv")
OUTPUT_PATH = Path("reports/cumulative_incidence.png")

TIME_POINTS = [30, 90, 180]


print("Loading cohort...")

df = pd.read_csv(COHORT_PATH)

print(f"Patients in cohort: {len(df)}")

print()
print("Event distribution:")
print(f"Censored: {(df['event'] == 0).sum()}")
print(f"Readmission: {(df['event'] == 1).sum()}")
print(f"Death: {(df['event'] == 2).sum()}")


event = df["event"].astype(int).to_numpy()
time = df["time_to_event_days"].astype(float).to_numpy()


time_points, cif = cumulative_incidence_competing_risks(
    event,
    time
)


readmission_cif = cif[1]
death_cif = cif[2]


print()
print("========================================")
print("CUMULATIVE INCIDENCE ANALYSIS")
print("========================================")

for target_time in TIME_POINTS:

    valid_indices = time_points <= target_time

    if valid_indices.any():
        index = valid_indices.nonzero()[0][-1]

        readmission_value = readmission_cif[index]
        death_value = death_cif[index]
    else:
        readmission_value = 0.0
        death_value = 0.0

    print()
    print(f"{target_time} days:")
    print(f"  Readmission probability: {readmission_value:.3f}")
    print(f"  Death probability: {death_value:.3f}")


plt.figure(figsize=(10, 6))

plt.step(
    time_points,
    readmission_cif,
    where="post",
    label="Readmission"
)

plt.step(
    time_points,
    death_cif,
    where="post",
    label="Death"
)

plt.xlabel("Days after index discharge")
plt.ylabel("Cumulative incidence")
plt.title("Competing Risks: Readmission vs Death")
plt.legend()
plt.grid(True, alpha=0.3)

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

plt.savefig(
    OUTPUT_PATH,
    dpi=150,
    bbox_inches="tight"
)

plt.close()

print()
print("Plot saved to:")
print(OUTPUT_PATH)
