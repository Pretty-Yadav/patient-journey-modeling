import pandas as pd
import ast
from pathlib import Path


# ---------------------------------------
# File paths
# ---------------------------------------

INPUT_PATH = Path(
    "data/processed/patient_pathway_tokens.csv"
)

OUTPUT_PATH = Path(
    "data/processed/patient_pathway_padded.csv"
)


# ---------------------------------------
# Load token sequences
# ---------------------------------------

df = pd.read_csv(INPUT_PATH)

df["token_sequence"] = df["token_sequence"].apply(
    ast.literal_eval
)


# ---------------------------------------
# Find maximum sequence length
# ---------------------------------------

max_length = df["token_sequence"].apply(len).max()

print("=" * 60)
print("PADDING PATIENT PATHWAY SEQUENCES")
print("=" * 60)

print(f"\nMaximum sequence length: {max_length}")


# ---------------------------------------
# Pad sequences with PAD token = 0
# ---------------------------------------

def pad_sequence(sequence, max_length):
    return sequence + [0] * (max_length - len(sequence))


df["padded_sequence"] = df["token_sequence"].apply(
    lambda sequence: pad_sequence(sequence, max_length)
)


# ---------------------------------------
# Create attention mask
# ---------------------------------------

def create_mask(sequence, max_length):
    return [1] * len(sequence) + [0] * (max_length - len(sequence))


df["attention_mask"] = df["token_sequence"].apply(
    lambda sequence: create_mask(sequence, max_length)
)


# ---------------------------------------
# Save output
# ---------------------------------------

output_df = df[
    [
        "subject_id",
        "padded_sequence",
        "attention_mask"
    ]
].copy()

output_df["padded_sequence"] = (
    output_df["padded_sequence"].apply(str)
)

output_df["attention_mask"] = (
    output_df["attention_mask"].apply(str)
)

output_df.to_csv(
    OUTPUT_PATH,
    index=False
)


# ---------------------------------------
# Display examples
# ---------------------------------------

print("\nExample padded sequences:")

for _, row in output_df.head(5).iterrows():

    print(f"\nPatient {row['subject_id']}")
    print("Padded sequence :", row["padded_sequence"])
    print("Attention mask  :", row["attention_mask"])


print("\nSaved to:")
print(OUTPUT_PATH)

print("=" * 60)
