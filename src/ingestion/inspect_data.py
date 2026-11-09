from src.cleaning.clean_data_types import clean_data_types
from src.ingestion.loader import load_csv


def main() -> None:
    file_name = "olist_orders_dataset.csv"
    orders = clean_data_types(load_csv(file_name), file_name)

    print("--- ORDERS DATASET ---")
    print("Shape:", orders.shape)
    print("Columns:", orders.columns.tolist())
    print("\nMissing values:")
    print(orders.isna().sum())
    print("\nOrder status distribution:")
    print(orders["order_status"].value_counts(dropna=False))

    missing_delivery = orders[
        orders["order_status"].eq("delivered")
        & orders["order_delivered_customer_date"].isna()
    ]
    print("\nDelivered orders with missing customer-delivery dates:", len(missing_delivery))
    duplicate_order_ids = int(orders["order_id"].duplicated().sum())
    print("Duplicate order IDs:", duplicate_order_ids)

    invalid_delivery_dates = orders[
        orders["order_delivered_customer_date"].notna()
        & orders["order_purchase_timestamp"].notna()
        & (
            orders["order_delivered_customer_date"]
            < orders["order_purchase_timestamp"]
        )
    ]
    print("Deliveries before purchase:", len(invalid_delivery_dates))


if __name__ == "__main__":
    main()
