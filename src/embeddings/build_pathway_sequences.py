import pandas as pd
from pathlib import Path


# ---------------------------------------
# File paths
# ---------------------------------------

INPUT_PATH = Path(
    "data/processed/patient_journey_180d.csv"
)

OUTPUT_PATH = Path(
    "data/processed/patient_pathway_sequences.csv"
)


# ---------------------------------------
# Load timeline
# ---------------------------------------

df = pd.read_csv(
    INPUT_PATH
)


# ---------------------------------------
# Sort events chronologically
# ---------------------------------------

df = df.sort_values(
    [
        "subject_id",
        "days_from_index",
        "event_type"
    ]
)


# ---------------------------------------
# Create event token
# ---------------------------------------

df["event_token"] = df["event_type"]


# ---------------------------------------
# Create patient sequences
# ---------------------------------------

sequences = (
    df.groupby("subject_id")["event_token"]
    .apply(list)
    .reset_index()
)


sequences = sequences.rename(
    columns={
        "event_token": "pathway_sequence"
    }
)


# ---------------------------------------
# Add sequence length
# ---------------------------------------

sequences["sequence_length"] = (
    sequences["pathway_sequence"].apply(len)
)


# ---------------------------------------
# Save
# ---------------------------------------

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)

sequences.to_csv(
    OUTPUT_PATH,
    index=False
)


# ---------------------------------------
# Display
# ---------------------------------------

print("=" * 60)
print("PATIENT PATHWAY SEQUENCES CREATED")
print("=" * 60)

print(
    f"Patients: {len(sequences)}"
)

print(
    f"Average sequence length: "
    f"{sequences['sequence_length'].mean():.2f}"
)

print(
    f"Maximum sequence length: "
    f"{sequences['sequence_length'].max()}"
)

print("\nExample patient sequences:")

for _, row in sequences.head(5).iterrows():

    print(
        f"\nPatient {row['subject_id']}"
    )

    print(
        row["pathway_sequence"]
    )

    print(
        f"Sequence length: "
        f"{row['sequence_length']}"
    )


print("\nSaved to:")
print(OUTPUT_PATH)

print("=" * 60)
