import logging

import pandas as pd


logger = logging.getLogger(__name__)

MISSING_VALUE_POLICIES = {
    "olist_orders_dataset.csv": {
        "order_approved_at": "Retain as missing; approval timestamps may be absent for canceled or incomplete orders.",
        "order_delivered_carrier_date": "Retain as missing; carrier handoff does not exist for undelivered orders.",
        "order_delivered_customer_date": "Retain as missing; customer delivery does not exist for undelivered orders.",
    },
    "olist_order_reviews_dataset.csv": {
        "review_comment_title": "Retain as missing; review text is optional.",
        "review_comment_message": "Retain as missing; review text is optional.",
    },
    "olist_products_dataset.csv": {
        "product_category_name": "Retain as missing; the source does not provide a category for every product.",
        "product_name_lenght": "Retain as missing; source product metadata is incomplete.",
        "product_description_lenght": "Retain as missing; source product metadata is incomplete.",
        "product_photos_qty": "Retain as missing; source product metadata is incomplete.",
        "product_weight_g": "Retain as missing; source product dimensions are incomplete.",
        "product_length_cm": "Retain as missing; source product dimensions are incomplete.",
        "product_height_cm": "Retain as missing; source product dimensions are incomplete.",
        "product_width_cm": "Retain as missing; source product dimensions are incomplete.",
    },
}

MISSING_REPORT_COLUMNS = [
    "dataset",
    "column",
    "missing_count",
    "policy",
    "reporting_stage",
]
MISSING_VALUE_REPORTING_STAGE = (
    "After type conversion and blank-string normalization; before duplicate handling"
)


def handle_missing_values(
    datasets: dict[str, pd.DataFrame],
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    cleaned: dict[str, pd.DataFrame] = {}
    report_rows: list[dict[str, object]] = []

    for file_name, original in datasets.items():
        df = original.copy()
        text_columns = df.select_dtypes(include=["object", "string"]).columns
        for column in text_columns:
            df[column] = df[column].replace(r"^\s*$", pd.NA, regex=True)

        for column in df.columns:
            missing_count = int(df[column].isna().sum())
            if not missing_count:
                continue
            policy = MISSING_VALUE_POLICIES.get(file_name, {}).get(
                column,
                "Retain as missing; no imputation or row removal is applied.",
            )
            report_rows.append(
                {
                    "dataset": file_name,
                    "column": column,
                    "missing_count": missing_count,
                    "policy": policy,
                    "reporting_stage": MISSING_VALUE_REPORTING_STAGE,
                }
            )
            logger.info(
                "%s.%s has %s missing value(s); preserving them. Policy: %s",
                file_name,
                column,
                missing_count,
                policy,
            )

        if len(df) != len(original):
            raise RuntimeError(f"Missing-value handling unexpectedly changed rows in {file_name}")
        cleaned[file_name] = df

    return cleaned, pd.DataFrame(report_rows, columns=MISSING_REPORT_COLUMNS)
