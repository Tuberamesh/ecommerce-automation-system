import pandas as pd


def build_order_item_fact(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    items = datasets["olist_order_items_dataset.csv"].copy()
    orders = datasets["olist_orders_dataset.csv"][
        [
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_estimated_delivery_date",
            "order_delivered_customer_date",
        ]
    ]
    products = datasets["olist_products_dataset.csv"]
    customers = datasets["olist_customers_dataset.csv"][
        ["customer_id", "customer_unique_id", "customer_city", "customer_state"]
    ]
    sellers = datasets["olist_sellers_dataset.csv"][
        ["seller_id", "seller_city", "seller_state"]
    ]
    translations = datasets["product_category_name_translation.csv"]

    fact = items.merge(orders, on="order_id", how="left", validate="many_to_one")
    fact = fact.merge(products, on="product_id", how="left", validate="many_to_one")
    fact = fact.merge(
        translations,
        on="product_category_name",
        how="left",
        validate="many_to_one",
    )
    fact = fact.merge(sellers, on="seller_id", how="left", validate="many_to_one")
    fact = fact.merge(customers, on="customer_id", how="left", validate="many_to_one")

    if len(fact) != len(items):
        raise RuntimeError(
            f"Order-item transformation changed row count: {len(items)} to {len(fact)}"
        )
    return fact
