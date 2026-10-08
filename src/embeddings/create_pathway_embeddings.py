import pandas as pd
import ast
import torch
import torch.nn as nn
from pathlib import Path


# ---------------------------------------
# File paths
# ---------------------------------------

INPUT_PATH = Path(
    "data/processed/patient_pathway_padded.csv"
)

OUTPUT_PATH = Path(
    "data/processed/patient_pathway_embeddings.csv"
)


# ---------------------------------------
# Model settings
# ---------------------------------------

VOCAB_SIZE = 4
EMBEDDING_DIM = 16


# ---------------------------------------
# Load padded sequences
# ---------------------------------------

df = pd.read_csv(INPUT_PATH)

df["padded_sequence"] = df["padded_sequence"].apply(
    ast.literal_eval
)

df["attention_mask"] = df["attention_mask"].apply(
    ast.literal_eval
)


# ---------------------------------------
# Create PyTorch tensors
# ---------------------------------------

sequences = torch.tensor(
    df["padded_sequence"].tolist(),
    dtype=torch.long
)

masks = torch.tensor(
    df["attention_mask"].tolist(),
    dtype=torch.float32
)


# ---------------------------------------
# Embedding model
# ---------------------------------------

class PathwayEmbedding(nn.Module):

    def __init__(self, vocab_size, embedding_dim):

        super().__init__()

        self.embedding = nn.Embedding(
            num_embeddings=vocab_size,
            embedding_dim=embedding_dim,
            padding_idx=0
        )

    def forward(self, sequences, masks):

        embeddings = self.embedding(sequences)

        # Ignore PAD tokens
        masks = masks.unsqueeze(-1)

        masked_embeddings = embeddings * masks

        # Average only real events
        sequence_lengths = masks.sum(
            dim=1
        ).clamp(min=1)

        patient_embedding = (
            masked_embeddings.sum(dim=1)
            / sequence_lengths
        )

        return patient_embedding


# ---------------------------------------
# Create model
# ---------------------------------------

model = PathwayEmbedding(
    VOCAB_SIZE,
    EMBEDDING_DIM
)


# ---------------------------------------
# Generate patient embeddings
# ---------------------------------------

with torch.no_grad():

    patient_embeddings = model(
        sequences,
        masks
    )


# ---------------------------------------
# Convert to DataFrame
# ---------------------------------------

embedding_columns = [
    f"embedding_{i}"
    for i in range(EMBEDDING_DIM)
]

embedding_df = pd.DataFrame(
    patient_embeddings.numpy(),
    columns=embedding_columns
)

embedding_df.insert(
    0,
    "subject_id",
    df["subject_id"].values
)


# ---------------------------------------
# Save embeddings
# ---------------------------------------

embedding_df.to_csv(
    OUTPUT_PATH,
    index=False
)


# ---------------------------------------
# Display results
# ---------------------------------------

print("=" * 60)
print("PATIENT PATHWAY EMBEDDINGS CREATED")
print("=" * 60)

print("\nPatients:", len(embedding_df))

print(
    "Embedding dimension:",
    EMBEDDING_DIM
)

print(
    "Embedding shape:",
    patient_embeddings.shape
)

print("\nFirst patient embedding:")

print(
    embedding_df.head(1).to_string(index=False)
)

print("\nSaved to:")
print(OUTPUT_PATH)

print("=" * 60)
