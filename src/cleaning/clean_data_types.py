
import pandas as pd


DATE_COLUMNS = {
    "olist_orders_dataset.csv": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "olist_order_items_dataset.csv": [
        "shipping_limit_date",
    ],
    "olist_order_reviews_dataset.csv": [
        "review_creation_date",
        "review_answer_timestamp",
    ],
}


INTEGER_COLUMNS = {
    "olist_order_items_dataset.csv": ["order_item_id"],
    "olist_order_payments_dataset.csv": [
        "payment_sequential",
        "payment_installments",
    ],
    "olist_order_reviews_dataset.csv": ["review_score"],
    "olist_products_dataset.csv": [
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ],
}

ZIP_COLUMNS = {
    "olist_sellers_dataset.csv": ["seller_zip_code_prefix"],
    "olist_customers_dataset.csv": ["customer_zip_code_prefix"],
    "olist_geolocation_dataset.csv": ["geolocation_zip_code_prefix"],
}


def clean_data_types(df: pd.DataFrame, file_name: str) -> pd.DataFrame:
    df = df.copy()

    for column in DATE_COLUMNS.get(file_name, []):
        if column not in df.columns:
            raise KeyError(f"{file_name} is missing expected date column {column!r}")
        source = df[column]
        converted = pd.to_datetime(source, errors="coerce")
        invalid = source.notna() & converted.isna()
        if invalid.any():
            samples = source.loc[invalid].head(5).tolist()
            raise ValueError(
                f"{file_name}.{column} contains {int(invalid.sum())} invalid date value(s); "
                f"examples: {samples}"
            )
        df[column] = converted

    for column in ZIP_COLUMNS.get(file_name, []):
        if column not in df.columns:
            raise KeyError(f"{file_name} is missing expected ZIP prefix column {column!r}")
        values = df[column].astype("string").str.strip()
        values = values.str.replace(r"\.0$", "", regex=True)
        df[column] = values.str.zfill(5)

    for column in INTEGER_COLUMNS.get(file_name, []):
        if column not in df.columns:
            raise KeyError(f"{file_name} is missing expected integer column {column!r}")
        source = df[column]
        numeric = pd.to_numeric(source, errors="coerce")
        invalid = source.notna() & numeric.isna()
        fractional = numeric.notna() & numeric.mod(1).ne(0)
        if invalid.any() or fractional.any():
            bad_values = source.loc[invalid | fractional].head(5).tolist()
            raise ValueError(
                f"{file_name}.{column} contains non-integer value(s); examples: {bad_values}"
            )
        df[column] = numeric.astype("Int64")

    return df
