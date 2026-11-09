import pandas as pd

from src.cleaning.clean_data_types import clean_data_types
from src.cleaning.handle_missing_values import (
    MISSING_VALUE_REPORTING_STAGE,
    handle_missing_values,
)
from src.ingestion.loader import RAW_DATA_DIR, load_all_datasets


def profile_dataset(df: pd.DataFrame, file_name: str) -> pd.DataFrame:
    row_count, column_count = df.shape
    duplicate_count = int(df.duplicated().sum())
    return pd.DataFrame(
        [
            {
                "dataset": file_name,
                "reporting_stage": MISSING_VALUE_REPORTING_STAGE,
                "column": column,
                "data_type": str(df[column].dtype),
                "row_count": row_count,
                "column_count": column_count,
                "missing_count": int(df[column].isna().sum()),
                "missing_pct": (
                    round(float(df[column].isna().mean() * 100), 2) if row_count else 0.0
                ),
                "exact_duplicate_rows": duplicate_count,
            }
            for column in df.columns
        ]
    )


def profile_datasets(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    profiles = [
        profile_dataset(df, file_name)
        for file_name, df in datasets.items()
    ]
    if not profiles:
        return pd.DataFrame(
            columns=[
                "dataset",
                "reporting_stage",
                "column",
                "data_type",
                "row_count",
                "column_count",
                "missing_count",
                "missing_pct",
                "exact_duplicate_rows",
            ]
        )
    return pd.concat(profiles, ignore_index=True)


def main() -> None:
    datasets = load_all_datasets(RAW_DATA_DIR)
    typed_datasets = {
        file_name: clean_data_types(df, file_name)
        for file_name, df in datasets.items()
    }
    normalized_datasets, _ = handle_missing_values(typed_datasets)
    profile = profile_datasets(normalized_datasets)
    print(f"Missing-value reporting stage: {MISSING_VALUE_REPORTING_STAGE}")
    for file_name, dataset_profile in profile.groupby("dataset", sort=True):
        print(f"\n--- DATA QUALITY PROFILE: {file_name} ---")
        print(
            dataset_profile[
                ["column", "data_type", "missing_count", "missing_pct"]
            ].to_string(index=False)
        )
        print(
            "Rows:",
            int(dataset_profile["row_count"].iloc[0]),
            "| Exact duplicate rows:",
            int(dataset_profile["exact_duplicate_rows"].iloc[0]),
        )


if __name__ == "__main__":
    main()