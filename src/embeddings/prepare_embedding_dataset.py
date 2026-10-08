import pandas as pd
from pathlib import Path


# ---------------------------------------
# File paths
# ---------------------------------------

EMBEDDING_PATH = Path(
    "data/processed/patient_pathway_embeddings.csv"
)

COHORT_PATH = Path(
    "data/processed/cohort.csv"
)

OUTPUT_PATH = Path(
    "data/processed/pathway_embedding_dataset.csv"
)


# ---------------------------------------
# Load data
# ---------------------------------------

embeddings = pd.read_csv(EMBEDDING_PATH)
cohort = pd.read_csv(COHORT_PATH)


# ---------------------------------------
# Select outcome information
# ---------------------------------------

outcomes = cohort[
    [
        "subject_id",
        "event",
        "event_label",
        "time_to_event_days"
    ]
].copy()


# ---------------------------------------
# Create binary outcome indicators
# ---------------------------------------

outcomes["readmission"] = (
    outcomes["event"] == 1
).astype(int)

outcomes["death"] = (
    outcomes["event"] == 2
).astype(int)


# ---------------------------------------
# Merge embeddings + outcomes
# ---------------------------------------

dataset = embeddings.merge(
    outcomes,
    on="subject_id",
    how="inner"
)


# ---------------------------------------
# Save dataset
# ---------------------------------------

dataset.to_csv(
    OUTPUT_PATH,
    index=False
)


# ---------------------------------------
# Display results
# ---------------------------------------

print("=" * 60)
print("PATHWAY EMBEDDING DATASET CREATED")
print("=" * 60)

print("\nDataset shape:")
print(dataset.shape)

print("\nEvent distribution:")
print(dataset["event_label"].value_counts())

print("\nReadmission distribution:")
print(dataset["readmission"].value_counts())

print("\nDeath distribution:")
print(dataset["death"].value_counts())

print("\nFirst 5 patients:")

print(
    dataset[
        [
            "subject_id",
            "event",
            "event_label",
            "readmission",
            "death",
            "time_to_event_days"
        ]
    ].head().to_string(index=False)
)

print("\nSaved to:")
print(OUTPUT_PATH)

print("=" * 60)
