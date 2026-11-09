import logging

import pandas as pd


logger = logging.getLogger(__name__)

BUSINESS_KEYS = {
    "olist_customers_dataset.csv": ["customer_id"],
    "olist_order_items_dataset.csv": ["order_id", "order_item_id"],
    "olist_order_payments_dataset.csv": ["order_id", "payment_sequential"],
    "olist_orders_dataset.csv": ["order_id"],
    "olist_products_dataset.csv": ["product_id"],
    "olist_sellers_dataset.csv": ["seller_id"],
    "product_category_name_translation.csv": ["product_category_name"],
}

EXACT_DUPLICATES_TO_REMOVE = {"olist_geolocation_dataset.csv"}
DUPLICATE_REPORT_COLUMNS = [
    "dataset",
    "business_key",
    "exact_duplicate_rows",
    "business_key_duplicate_rows",
    "exact_rows_removed",
    "handling",
]


def handle_duplicates(
    datasets: dict[str, pd.DataFrame],
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    cleaned: dict[str, pd.DataFrame] = {}
    report_rows: list[dict[str, object]] = []

    for file_name, original in datasets.items():
        exact_duplicates = int(original.duplicated().sum())
        key_columns = BUSINESS_KEYS.get(file_name, [])
        missing_key_columns = [column for column in key_columns if column not in original.columns]
        if missing_key_columns:
            raise KeyError(
                f"{file_name} is missing business key column(s): {', '.join(missing_key_columns)}"
            )
        key_duplicates = (
            int(original.duplicated(subset=key_columns).sum()) if key_columns else 0
        )

        if file_name in EXACT_DUPLICATES_TO_REMOVE:
            df = original.drop_duplicates().copy()
            removed = len(original) - len(df)
            handling = "Removed exact duplicate rows; first occurrence retained."
            if removed:
                logger.warning(
                    "Removed %s exact duplicate row(s) from %s; retained first occurrences.",
                    removed,
                    file_name,
                )
        else:
            df = original.copy()
            removed = 0
            handling = "Retained rows; reported exact and business-key duplicates."
            if exact_duplicates or key_duplicates:
                logger.warning(
                    "%s has %s exact and %s business-key duplicate row(s); records retained.",
                    file_name,
                    exact_duplicates,
                    key_duplicates,
                )

        if len(df) != len(original) - removed:
            raise RuntimeError(f"Duplicate handling row-count check failed for {file_name}")
        cleaned[file_name] = df
        report_rows.append(
            {
                "dataset": file_name,
                "business_key": ", ".join(key_columns) if key_columns else "Not defined",
                "exact_duplicate_rows": exact_duplicates,
                "business_key_duplicate_rows": key_duplicates,
                "exact_rows_removed": removed,
                "handling": handling,
            }
        )

    return cleaned, pd.DataFrame(report_rows, columns=DUPLICATE_REPORT_COLUMNS)
