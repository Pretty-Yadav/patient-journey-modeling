import pandas as pd
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    roc_auc_score,
    brier_score_loss
)


# ---------------------------------------
# File paths
# ---------------------------------------

INPUT_PATH = Path(
    "data/processed/pathway_embedding_dataset.csv"
)


# ---------------------------------------
# Load dataset
# ---------------------------------------

df = pd.read_csv(INPUT_PATH)


# ---------------------------------------
# Select embedding features
# ---------------------------------------

embedding_columns = [
    column
    for column in df.columns
    if column.startswith("embedding_")
]

X = df[embedding_columns]

y = df["readmission"]


# ---------------------------------------
# Train-test split
# ---------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.25,
    random_state=42,
    stratify=y
)


# ---------------------------------------
# Train Logistic Regression
# ---------------------------------------

model = LogisticRegression(
    max_iter=1000,
    class_weight="balanced",
    random_state=42
)

model.fit(
    X_train,
    y_train
)


# ---------------------------------------
# Predictions
# ---------------------------------------

predictions = model.predict(X_test)

probabilities = model.predict_proba(
    X_test
)[:, 1]


# ---------------------------------------
# Evaluation
# ---------------------------------------

accuracy = accuracy_score(
    y_test,
    predictions
)

precision = precision_score(
    y_test,
    predictions,
    zero_division=0
)

recall = recall_score(
    y_test,
    predictions,
    zero_division=0
)

brier = brier_score_loss(
    y_test,
    probabilities
)

print("=" * 60)
print("PATHWAY EMBEDDING BASELINE")
print("=" * 60)

print("\nEmbedding features:", len(embedding_columns))

print("Training patients:", len(X_train))
print("Test patients:", len(X_test))

print("\nPerformance:")

print(f"Accuracy : {accuracy:.3f}")
print(f"Precision: {precision:.3f}")
print(f"Recall   : {recall:.3f}")
print(f"Brier    : {brier:.3f}")

if len(y_test.unique()) == 2:

    auc = roc_auc_score(
        y_test,
        probabilities
    )

    print(f"ROC-AUC  : {auc:.3f}")

else:

    print("ROC-AUC  : Not available")


print("\n" + "=" * 60)
