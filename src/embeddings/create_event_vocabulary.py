import pandas as pd
from pathlib import Path


INPUT_PATH = Path(
    "data/processed/patient_pathway_sequences.csv"
)

OUTPUT_PATH = Path(
    "data/processed/patient_pathway_tokens.csv"
)

VOCAB_PATH = Path(
    "data/processed/event_vocabulary.csv"
)


# ---------------------------------------
# Load sequences
# ---------------------------------------

df = pd.read_csv(INPUT_PATH)


# ---------------------------------------
# Define event vocabulary
# ---------------------------------------

vocabulary = {
    "PAD": 0,
    "hospital_admission": 1,
    "hospital_discharge": 2,
    "diagnosis": 3
}


# ---------------------------------------
# Convert sequence strings back to lists
# ---------------------------------------

import ast

df["pathway_sequence"] = df["pathway_sequence"].apply(
    ast.literal_eval
)


# ---------------------------------------
# Convert events to numerical tokens
# ---------------------------------------

df["token_sequence"] = df["pathway_sequence"].apply(
    lambda sequence: [
        vocabulary[event]
        for event in sequence
    ]
)


# ---------------------------------------
# Save token sequences
# ---------------------------------------

output_df = df[
    [
        "subject_id",
        "token_sequence",
        "sequence_length"
    ]
].copy()

output_df["token_sequence"] = (
    output_df["token_sequence"].apply(str)
)

output_df.to_csv(
    OUTPUT_PATH,
    index=False
)


# ---------------------------------------
# Save vocabulary
# ---------------------------------------

vocab_df = pd.DataFrame(
    [
        {
            "event": event,
            "token_id": token_id
        }
        for event, token_id in vocabulary.items()
    ]
)

vocab_df.to_csv(
    VOCAB_PATH,
    index=False
)


# ---------------------------------------
# Display results
# ---------------------------------------

print("=" * 60)
print("EVENT VOCABULARY CREATED")
print("=" * 60)

print("\nVocabulary:")

for event, token_id in vocabulary.items():
    print(f"{event} -> {token_id}")


print("\nExample token sequences:")

for _, row in output_df.head(5).iterrows():

    print(
        f"Patient {row['subject_id']}: "
        f"{row['token_sequence']}"
    )


print("\nSaved token sequences to:")
print(OUTPUT_PATH)

print("\nSaved vocabulary to:")
print(VOCAB_PATH)

print("=" * 60)
