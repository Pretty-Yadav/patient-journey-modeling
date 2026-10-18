from __future__ import annotations

import pandas as pd
from sklearn.model_selection import train_test_split


def create_patient_level_split(
    dataset: pd.DataFrame,
    *,
    feature_columns: list[str],
    target_column: str,
    patient_id_column: str = "subject_id",
    test_size: float = 0.25,
    random_seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required_columns = [patient_id_column, *feature_columns, target_column]
    missing_columns = [column for column in required_columns if column not in dataset.columns]
    if missing_columns:
        raise ValueError(f"Dataset is missing required columns: {missing_columns}")
    if dataset.empty:
        raise ValueError("Dataset must contain at least one patient.")
    if dataset[patient_id_column].isna().any() or dataset[patient_id_column].duplicated().any():
        raise ValueError("Each patient must have exactly one non-missing row before splitting.")

    targets = dataset[target_column]
    if targets.isna().any() or not set(targets.unique()).issubset({0, 1}):
        raise ValueError(f"{target_column} must contain only non-missing binary labels 0 and 1.")
    class_counts = targets.value_counts()
    if len(class_counts) != 2 or class_counts.min() < 2:
        raise ValueError("Each target class must contain at least two patients for a stratified split.")

    split_columns = [patient_id_column, *feature_columns, target_column]
    train, test = train_test_split(
        dataset[split_columns],
        test_size=test_size,
        random_state=random_seed,
        stratify=targets,
    )
    return train.reset_index(drop=True), test.reset_index(drop=True)