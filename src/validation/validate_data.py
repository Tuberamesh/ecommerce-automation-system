import logging
from collections.abc import Iterable

import pandas as pd

from src.ingestion.loader import DATASET_FILES, REQUIRED_COLUMNS


logger = logging.getLogger(__name__)

PRIMARY_KEYS = {
    "olist_customers_dataset.csv": ["customer_id"],
    "olist_order_items_dataset.csv": ["order_id", "order_item_id"],
    "olist_order_payments_dataset.csv": ["order_id", "payment_sequential"],
    "olist_orders_dataset.csv": ["order_id"],
    "olist_products_dataset.csv": ["product_id"],
    "olist_sellers_dataset.csv": ["seller_id"],
    "product_category_name_translation.csv": ["product_category_name"],
}

VALIDATION_COLUMNS = ["dataset", "rule", "status", "failed_rows", "examples"]
ALLOWED_ORDER_STATUSES = {
    "approved",
    "canceled",
    "created",
    "delivered",
    "invoiced",
    "processing",
    "shipped",
    "unavailable",
}


def _examples(values: Iterable[object], limit: int = 5) -> str:
    return ", ".join(str(value) for value in list(values)[:limit])


def validate_datasets(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    results: list[dict[str, object]] = []

    def record(
        dataset: str,
        rule: str,
        failed_rows: int,
        examples: Iterable[object] = (),
        severity: str = "WARNING",
    ) -> None:
        status = severity if failed_rows else "PASS"
        result = {
            "dataset": dataset,
            "rule": rule,
            "status": status,
            "failed_rows": int(failed_rows),
            "examples": _examples(examples),
        }
        results.append(result)
        if failed_rows:
            logger.log(
                logging.ERROR if severity == "ERROR" else logging.WARNING,
                "%s: %s failed for %s row(s). Examples: %s",
                dataset,
                rule,
                failed_rows,
                result["examples"],
            )

    for file_name in DATASET_FILES:
        df = datasets.get(file_name)
        if df is None:
            record(file_name, "Required dataset is present", 1, [file_name], "ERROR")
            continue

        missing_columns = [column for column in REQUIRED_COLUMNS[file_name] if column not in df]
        record(
            file_name,
            "Required columns are present",
            len(missing_columns),
            missing_columns,
            "ERROR",
        )
        if missing_columns:
            continue

        keys = PRIMARY_KEYS.get(file_name, [])
        for column in keys:
            missing_mask = df[column].isna()
            record(
                file_name,
                f"Required key {column} is not null",
                int(missing_mask.sum()),
                df.loc[missing_mask, column].head().tolist(),
                "ERROR",
            )
        if keys:
            duplicate_mask = df.duplicated(subset=keys, keep="first")
            duplicate_examples = (
                df.loc[duplicate_mask, keys]
                .head()
                .astype("string")
                .fillna("<NULL>")
                .to_dict("records")
            )
            record(
                file_name,
                f"Business key ({', '.join(keys)}) is unique",
                int(duplicate_mask.sum()),
                duplicate_examples,
            )

    for file_name, column in (
        ("olist_order_items_dataset.csv", "price"),
        ("olist_order_items_dataset.csv", "freight_value"),
        ("olist_order_payments_dataset.csv", "payment_value"),
    ):
        df = datasets.get(file_name)
        if df is not None and column in df:
            invalid = df[column].notna() & df[column].lt(0)
            record(file_name, f"{column} is non-negative", int(invalid.sum()), df.loc[invalid, column])

    reviews = datasets.get("olist_order_reviews_dataset.csv")
    if reviews is not None and {"review_id", "review_score"}.issubset(reviews.columns):
        repeated_id_mask = reviews.duplicated(subset=["review_id"], keep="first")
        repeated_ids = (
            reviews.loc[repeated_id_mask, "review_id"]
            .astype("string")
            .head()
            .tolist()
        )
        record(
            "olist_order_reviews_dataset.csv",
            "Review ID appears on multiple rows (records retained; not assumed duplicates)",
            int(repeated_id_mask.sum()),
            repeated_ids,
        )
        invalid = reviews["review_score"].notna() & ~reviews["review_score"].between(1, 5)
        record(
            "olist_order_reviews_dataset.csv",
            "review_score is between 1 and 5",
            int(invalid.sum()),
            reviews.loc[invalid, "review_score"],
        )

    products = datasets.get("olist_products_dataset.csv")
    if products is not None:
        for column in (
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ):
            if column in products:
                invalid = products[column].notna() & products[column].le(0)
                record(
                    "olist_products_dataset.csv",
                    f"{column} is positive when present",
                    int(invalid.sum()),
                    products.loc[invalid, column],
                )

    orders = datasets.get("olist_orders_dataset.csv")
    if orders is not None:
        if "order_status" in orders:
            invalid_status = orders["order_status"].notna() & ~orders["order_status"].isin(
                ALLOWED_ORDER_STATUSES
            )
            record(
                "olist_orders_dataset.csv",
                "order_status is recognized",
                int(invalid_status.sum()),
                orders.loc[invalid_status, "order_status"].unique(),
            )
        for earlier, later in (
            ("order_purchase_timestamp", "order_approved_at"),
            ("order_purchase_timestamp", "order_delivered_carrier_date"),
            ("order_purchase_timestamp", "order_delivered_customer_date"),
            ("order_delivered_carrier_date", "order_delivered_customer_date"),
        ):
            if earlier in orders and later in orders:
                invalid_dates = orders[later].notna() & orders[earlier].notna() & (
                    orders[later] < orders[earlier]
                )
                record(
                    "olist_orders_dataset.csv",
                    f"{later} is not before {earlier}",
                    int(invalid_dates.sum()),
                    orders.loc[invalid_dates, "order_id"],
                )

    foreign_keys = (
        ("olist_orders_dataset.csv", "customer_id", "olist_customers_dataset.csv", "customer_id"),
        ("olist_order_items_dataset.csv", "order_id", "olist_orders_dataset.csv", "order_id"),
        ("olist_order_items_dataset.csv", "product_id", "olist_products_dataset.csv", "product_id"),
        ("olist_order_items_dataset.csv", "seller_id", "olist_sellers_dataset.csv", "seller_id"),
        ("olist_order_payments_dataset.csv", "order_id", "olist_orders_dataset.csv", "order_id"),
        ("olist_order_reviews_dataset.csv", "order_id", "olist_orders_dataset.csv", "order_id"),
    )
    for child_name, child_column, parent_name, parent_column in foreign_keys:
        child = datasets.get(child_name)
        parent = datasets.get(parent_name)
        if (
            child is None
            or parent is None
            or child_column not in child
            or parent_column not in parent
        ):
            continue
        invalid = child[child_column].notna() & ~child[child_column].isin(parent[parent_column])
        record(
            child_name,
            f"{child_column} references {parent_name}.{parent_column}",
            int(invalid.sum()),
            child.loc[invalid, child_column],
        )

    return pd.DataFrame(results, columns=VALIDATION_COLUMNS)
