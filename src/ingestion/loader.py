from pathlib import Path
import logging

import pandas as pd


logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

DATASET_FILES = (
    "olist_customers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
)

REQUIRED_COLUMNS = {
    "olist_customers_dataset.csv": (
        "customer_id",
        "customer_unique_id",
        "customer_zip_code_prefix",
        "customer_city",
        "customer_state",
    ),
    "olist_geolocation_dataset.csv": (
        "geolocation_zip_code_prefix",
        "geolocation_lat",
        "geolocation_lng",
        "geolocation_city",
        "geolocation_state",
    ),
    "olist_order_items_dataset.csv": (
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "shipping_limit_date",
        "price",
        "freight_value",
    ),
    "olist_order_payments_dataset.csv": (
        "order_id",
        "payment_sequential",
        "payment_type",
        "payment_installments",
        "payment_value",
    ),
    "olist_order_reviews_dataset.csv": (
        "review_id",
        "order_id",
        "review_score",
        "review_comment_title",
        "review_comment_message",
        "review_creation_date",
        "review_answer_timestamp",
    ),
    "olist_orders_dataset.csv": (
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ),
    "olist_products_dataset.csv": (
        "product_id",
        "product_category_name",
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ),
    "olist_sellers_dataset.csv": (
        "seller_id",
        "seller_zip_code_prefix",
        "seller_city",
        "seller_state",
    ),
    "product_category_name_translation.csv": (
        "product_category_name",
        "product_category_name_english",
    ),
}


def load_csv(file_name: str, data_dir: Path | str = RAW_DATA_DIR) -> pd.DataFrame:
    if Path(file_name).name != file_name or Path(file_name).suffix.lower() != ".csv":
        raise ValueError(f"Expected a CSV file name, got: {file_name!r}")

    file_path = Path(data_dir) / file_name

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not file_path.is_file():
        raise FileNotFoundError(f"Expected a file, got: {file_path}")

    try:
        df = pd.read_csv(file_path)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError):
        logger.exception("Could not read dataset %s", file_path)
        raise

    logger.info("Loaded %s with %s rows and %s columns", file_name, *df.shape)
    return df


def load_all_datasets(data_dir: Path | str = RAW_DATA_DIR) -> dict[str, pd.DataFrame]:
    directory = Path(data_dir)
    missing_files = [name for name in DATASET_FILES if not (directory / name).is_file()]
    if missing_files:
        missing_list = ", ".join(missing_files)
        raise FileNotFoundError(f"Required dataset files are missing from {directory}: {missing_list}")

    return {file_name: load_csv(file_name, directory) for file_name in DATASET_FILES}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    loaded_datasets = load_all_datasets()
    logger.info("Loaded all %s required datasets", len(loaded_datasets))