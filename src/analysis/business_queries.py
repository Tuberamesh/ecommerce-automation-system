import logging
import sqlite3
from pathlib import Path

import pandas as pd

from src.database.storage import DEFAULT_DATABASE_PATH


logger = logging.getLogger(__name__)

BUSINESS_QUERIES = {
    "Monthly Sales (Delivered+All)": """
        SELECT
            strftime('%Y-%m', o.order_purchase_timestamp) AS month,
            COUNT(DISTINCT CASE WHEN o.order_status = 'delivered' THEN o.order_id END)
                AS delivered_order_count,
            SUM(CASE WHEN o.order_status = 'delivered' THEN 1 ELSE 0 END)
                AS delivered_item_count,
            ROUND(SUM(CASE WHEN o.order_status = 'delivered' THEN i.price ELSE 0 END), 2)
                AS delivered_item_revenue,
            ROUND(SUM(CASE WHEN o.order_status = 'delivered' THEN i.freight_value ELSE 0 END), 2)
                AS delivered_freight,
            ROUND(SUM(CASE WHEN o.order_status = 'delivered'
                THEN i.price + i.freight_value ELSE 0 END), 2)
                AS delivered_total_value,
            COUNT(DISTINCT o.order_id) AS all_status_order_count_with_items,
            COUNT(i.order_id) AS all_status_item_count,
            ROUND(SUM(i.price + i.freight_value), 2) AS all_status_item_value
        FROM olist_orders_dataset AS o
        JOIN olist_order_items_dataset AS i ON i.order_id = o.order_id
        GROUP BY month
        ORDER BY month
    """,
    "Sales by State (Delivered+All)": """
        SELECT
            c.customer_state,
            COUNT(DISTINCT o.order_id) AS all_status_order_count,
            COUNT(DISTINCT CASE WHEN o.order_status = 'delivered' THEN o.order_id END)
                AS delivered_order_count,
            ROUND(SUM(COALESCE(i.price, 0)), 2) AS all_status_item_price,
            ROUND(SUM(COALESCE(i.freight_value, 0)), 2) AS all_status_freight,
            ROUND(SUM(COALESCE(i.price, 0) + COALESCE(i.freight_value, 0)), 2)
                AS all_status_item_value,
            ROUND(SUM(CASE WHEN o.order_status = 'delivered'
                THEN COALESCE(i.price, 0) ELSE 0 END), 2)
                AS delivered_item_revenue,
            ROUND(SUM(CASE WHEN o.order_status = 'delivered'
                THEN COALESCE(i.freight_value, 0) ELSE 0 END), 2)
                AS delivered_freight,
            ROUND(SUM(CASE WHEN o.order_status = 'delivered'
                THEN COALESCE(i.price, 0) + COALESCE(i.freight_value, 0) ELSE 0 END), 2)
                AS delivered_total_value
        FROM olist_orders_dataset AS o
        JOIN olist_customers_dataset AS c ON c.customer_id = o.customer_id
        LEFT JOIN olist_order_items_dataset AS i ON i.order_id = o.order_id
        GROUP BY c.customer_state
        ORDER BY delivered_total_value DESC
    """,
    "Top Categories (Delivered+All)": """
        SELECT
            t.product_category_name_english AS category,
            COUNT(*) AS all_status_item_count,
            COUNT(DISTINCT i.order_id) AS all_status_order_count,
            ROUND(SUM(i.price), 2) AS all_status_item_price,
            ROUND(SUM(i.freight_value), 2) AS all_status_freight,
            ROUND(SUM(i.price + i.freight_value), 2) AS all_status_item_value,
            SUM(CASE WHEN o.order_status = 'delivered' THEN 1 ELSE 0 END)
                AS delivered_item_count,
            COUNT(DISTINCT CASE WHEN o.order_status = 'delivered' THEN o.order_id END)
                AS delivered_order_count,
            ROUND(SUM(CASE WHEN o.order_status = 'delivered' THEN i.price ELSE 0 END), 2)
                AS delivered_item_revenue,
            ROUND(SUM(CASE WHEN o.order_status = 'delivered' THEN i.freight_value ELSE 0 END), 2)
                AS delivered_freight,
            ROUND(SUM(CASE WHEN o.order_status = 'delivered'
                THEN i.price + i.freight_value ELSE 0 END), 2)
                AS delivered_total_value
        FROM olist_order_items_dataset AS i
        JOIN olist_orders_dataset AS o ON o.order_id = i.order_id
        JOIN olist_products_dataset AS p ON p.product_id = i.product_id
        LEFT JOIN product_category_name_translation AS t
            ON t.product_category_name = p.product_category_name
        GROUP BY t.product_category_name_english
        ORDER BY delivered_total_value DESC
        LIMIT 20
    """,
    "Payment Reconciliation": """
        SELECT
            ROUND((SELECT SUM(payment_value)
                FROM olist_order_payments_dataset), 2) AS payment_value_all_statuses,
            ROUND((SELECT SUM(price)
                FROM olist_order_items_dataset), 2) AS item_price_total_all_statuses,
            ROUND((SELECT SUM(freight_value)
                FROM olist_order_items_dataset), 2) AS freight_total_all_statuses,
            ROUND((SELECT SUM(price + freight_value)
                FROM olist_order_items_dataset), 2) AS item_price_plus_freight_all_statuses,
            ROUND(
                (SELECT SUM(payment_value) FROM olist_order_payments_dataset)
                - (SELECT SUM(price + freight_value) FROM olist_order_items_dataset),
                2
            ) AS payment_minus_item_price_and_freight,
            'Different financial measures; a difference is not inherently an error and requires investigation.'
                AS interpretation
    """,
    "Payment Types": """
        SELECT
            payment_type,
            COUNT(*) AS payment_count,
            COUNT(DISTINCT order_id) AS order_count,
            ROUND(SUM(payment_value), 2) AS payment_value
        FROM olist_order_payments_dataset
        GROUP BY payment_type
        ORDER BY payment_value DESC
    """,
    "Review Scores": """
        SELECT
            review_score,
            COUNT(*) AS review_count
        FROM olist_order_reviews_dataset
        GROUP BY review_score
        ORDER BY review_score
    """,
    "Order Status": """
        SELECT order_status, COUNT(*) AS order_count
        FROM olist_orders_dataset
        GROUP BY order_status
        ORDER BY order_count DESC
    """,
}


def run_business_analysis(
    database_path: Path | str = DEFAULT_DATABASE_PATH,
) -> dict[str, pd.DataFrame]:
    path = Path(database_path)
    if not path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {path}")

    results: dict[str, pd.DataFrame] = {}
    connection = sqlite3.connect(path)
    try:
        for sheet_name, query in BUSINESS_QUERIES.items():
            results[sheet_name] = pd.read_sql_query(query, connection)
            logger.info("Executed business query %s (%s rows)", sheet_name, len(results[sheet_name]))
    except Exception:
        logger.exception("Business analysis failed for %s", path)
        raise
    finally:
        connection.close()
    return results
