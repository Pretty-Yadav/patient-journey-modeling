import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score


# Load predictions
df = pd.read_csv(
    "data/processed/xgboost_predictions.csv"
)


# Create age groups
df["age_group"] = df["anchor_age"].apply(
    lambda age: "Younger (<65)" if age < 65 else "Older (65+)"
)


results = []


def evaluate_group(group_name, group):
    """Calculate subgroup evaluation metrics."""

    patients = len(group)
    readmissions = int(group["readmission_180d"].sum())

    brier = brier_score_loss(
        group["readmission_180d"],
        group["predicted_probability"]
    )

    if group["readmission_180d"].nunique() == 2:
        auc = roc_auc_score(
            group["readmission_180d"],
            group["predicted_probability"]
        )
    else:
        auc = None

    results.append({
        "subgroup": group_name,
        "patients": patients,
        "readmissions": readmissions,
        "brier_score": round(brier, 4),
        "roc_auc": round(auc, 4) if auc is not None else None
    })


# Gender subgroups
evaluate_group(
    "Male",
    df[df["gender"] == 0]
)

evaluate_group(
    "Female",
    df[df["gender"] == 1]
)


# Age subgroups
evaluate_group(
    "Younger (<65)",
    df[df["age_group"] == "Younger (<65)"]
)

evaluate_group(
    "Older (65+)",
    df[df["age_group"] == "Older (65+)"]
)


# Convert results to DataFrame
results_df = pd.DataFrame(results)


# Save results
results_df.to_csv(
    "reports/subgroup_analysis.csv",
    index=False
)


# Display results
print("=" * 60)
print("XGBOOST SUBGROUP ANALYSIS")
print("=" * 60)

print(results_df.to_string(index=False))

print("\n" + "=" * 60)
print("Subgroup analysis saved to:")
print("reports/subgroup_analysis.csv")
print("=" * 60)
