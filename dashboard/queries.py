from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from dashboard.config import DATABASE_PATH
from dashboard.database import read_query


@dataclass(frozen=True)
class DashboardFilters:
    start_date: str | None = None
    end_date: str | None = None
    states: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    statuses: tuple[str, ...] = ()


def _in_clause(values: tuple[str, ...]) -> str:
    return ", ".join("?" for _ in values)


def _order_scope(
    filters: DashboardFilters,
    order_alias: str = "o",
) -> tuple[str, list[object]]:
    conditions: list[str] = []
    params: list[object] = []
    if filters.start_date:
        conditions.append(f"{order_alias}.order_purchase_timestamp >= ?")
        params.append(filters.start_date)
    if filters.end_date:
        conditions.append(
            f"{order_alias}.order_purchase_timestamp < date(?, '+1 day')"
        )
        params.append(filters.end_date)
    if filters.statuses:
        conditions.append(
            f"{order_alias}.order_status IN ({_in_clause(filters.statuses)})"
        )
        params.extend(filters.statuses)
    if filters.states:
        conditions.append(
            f"""EXISTS (
                SELECT 1 FROM olist_customers_dataset AS fc
                WHERE fc.customer_id = {order_alias}.customer_id
                  AND fc.customer_state IN ({_in_clause(filters.states)})
            )"""
        )
        params.extend(filters.states)
    if filters.categories:
        category = _category_expression("fp", "ft")
        conditions.append(
            f"""EXISTS (
                SELECT 1
                FROM olist_order_items_dataset AS fi
                JOIN olist_products_dataset AS fp ON fp.product_id = fi.product_id
                LEFT JOIN product_category_name_translation AS ft
                    ON ft.product_category_name = fp.product_category_name
                WHERE fi.order_id = {order_alias}.order_id
                  AND {category} IN ({_in_clause(filters.categories)})
            )"""
        )
        params.extend(filters.categories)
    return (" AND ".join(conditions) if conditions else "1 = 1"), params


def _category_expression(product_alias: str = "p", translation_alias: str = "t") -> str:
    return (
        f"COALESCE(NULLIF({translation_alias}.product_category_name_english, ''), "
        f"NULLIF({product_alias}.product_category_name, ''), 'Unknown')"
    )


def _item_category_scope(
    filters: DashboardFilters,
    product_alias: str = "p",
    translation_alias: str = "t",
) -> tuple[str, list[object]]:
    if not filters.categories:
        return "1 = 1", []
    expression = _category_expression(product_alias, translation_alias)
    return f"{expression} IN ({_in_clause(filters.categories)})", list(filters.categories)


def _run(
    sql: str,
    params: list[object] | tuple[object, ...] = (),
    database_path: str | None = None,
) -> pd.DataFrame:
    return read_query(
        sql,
        tuple(params),
        str(database_path or DATABASE_PATH),
    )


def get_filter_options(database_path: str | None = None) -> dict[str, Any]:
    path = str(database_path or DATABASE_PATH)
    date_row = _run(
        """SELECT MIN(order_purchase_timestamp) AS min_date,
                  MAX(order_purchase_timestamp) AS max_date
           FROM olist_orders_dataset""",
        database_path=path,
    ).iloc[0]
    states = _run(
        """SELECT DISTINCT customer_state AS value
           FROM olist_customers_dataset
           WHERE customer_state IS NOT NULL
           ORDER BY customer_state""",
        database_path=path,
    )["value"].tolist()
    statuses = _run(
        """SELECT DISTINCT order_status AS value
           FROM olist_orders_dataset
           WHERE order_status IS NOT NULL
           ORDER BY order_status""",
        database_path=path,
    )["value"].tolist()
    categories = _run(
        f"""SELECT DISTINCT {_category_expression()} AS value
            FROM olist_products_dataset AS p
            LEFT JOIN product_category_name_translation AS t
                ON t.product_category_name = p.product_category_name
            ORDER BY value""",
        database_path=path,
    )["value"].tolist()
    return {
        "min_date": _date_part(date_row["min_date"]),
        "max_date": _date_part(date_row["max_date"]),
        "states": states,
        "statuses": statuses,
        "categories": categories,
    }


def _date_part(value: object) -> str | None:
    if pd.isna(value):
        return None
    return str(value)[:10]


def get_kpis(
    filters: DashboardFilters,
    database_path: str | None = None,
) -> dict[str, float | int]:
    scope, scope_params = _order_scope(filters)
    item_scope, item_params = _item_category_scope(filters)
    orders = _run(
        f"""SELECT COUNT(DISTINCT o.order_id) AS order_count,
                   COUNT(DISTINCT CASE WHEN o.order_status = 'delivered'
                       THEN o.order_id END) AS delivered_orders,
                   COUNT(DISTINCT c.customer_unique_id) AS customers
            FROM olist_orders_dataset AS o
            LEFT JOIN olist_customers_dataset AS c ON c.customer_id = o.customer_id
            WHERE {scope}""",
        scope_params,
        database_path,
    )
    money = _run(
        f"""SELECT
                COALESCE(SUM(CASE WHEN o.order_status = 'delivered'
                    THEN COALESCE(i.price, 0) ELSE 0 END), 0) AS delivered_revenue,
                COALESCE(SUM(CASE WHEN o.order_status = 'delivered'
                    THEN COALESCE(i.freight_value, 0) ELSE 0 END), 0) AS delivered_freight,
                COUNT(DISTINCT CASE WHEN o.order_status = 'delivered'
                    THEN o.order_id END) AS delivered_item_orders
            FROM olist_orders_dataset AS o
            JOIN olist_order_items_dataset AS i ON i.order_id = o.order_id
            LEFT JOIN olist_products_dataset AS p ON p.product_id = i.product_id
            LEFT JOIN product_category_name_translation AS t
                ON t.product_category_name = p.product_category_name
            WHERE {scope} AND {item_scope}""",
        [*scope_params, *item_params],
        database_path,
    ).iloc[0]
    row = orders.iloc[0]
    delivered_orders = int(row["delivered_orders"])
    revenue = float(money["delivered_revenue"])
    delivered_item_orders = int(money["delivered_item_orders"])
    return {
        "orders": int(row["order_count"]),
        "delivered_orders": delivered_orders,
        "customers": int(row["customers"]),
        "delivered_revenue": revenue,
        "delivered_freight": float(money["delivered_freight"]),
        "average_order_value": revenue / delivered_item_orders if delivered_item_orders else 0.0,
    }


def sales_trend(
    filters: DashboardFilters,
    grain: str = "month",
    database_path: str | None = None,
) -> pd.DataFrame:
    expressions = {
        "month": "strftime('%Y-%m', o.order_purchase_timestamp)",
        "quarter": (
            "strftime('%Y', o.order_purchase_timestamp) || '-Q' || "
            "CAST(((CAST(strftime('%m', o.order_purchase_timestamp) AS INTEGER) - 1) "
            "/ 3) + 1 AS INTEGER)"
        ),
        "year": "strftime('%Y', o.order_purchase_timestamp)",
    }
    if grain not in expressions:
        raise ValueError(f"Unsupported sales grain: {grain}")
    scope, scope_params = _order_scope(filters)
    item_scope, item_params = _item_category_scope(filters)
    return _run(
        f"""SELECT {expressions[grain]} AS period,
                   COUNT(DISTINCT CASE WHEN o.order_status = 'delivered'
                       THEN o.order_id END) AS delivered_orders,
                   COUNT(DISTINCT o.order_id) AS all_status_orders,
                   COALESCE(SUM(CASE WHEN o.order_status = 'delivered'
                       THEN COALESCE(i.price, 0) ELSE 0 END), 0) AS delivered_item_revenue,
                   COALESCE(SUM(CASE WHEN o.order_status = 'delivered'
                       THEN COALESCE(i.freight_value, 0) ELSE 0 END), 0) AS delivered_freight,
                   COALESCE(SUM(CASE WHEN o.order_status = 'delivered'
                       THEN COALESCE(i.price, 0) + COALESCE(i.freight_value, 0)
                       ELSE 0 END), 0) AS delivered_total_value,
                   COALESCE(SUM(COALESCE(i.price, 0) + COALESCE(i.freight_value, 0)),
                       0) AS all_status_item_value
            FROM olist_orders_dataset AS o
            JOIN olist_order_items_dataset AS i ON i.order_id = o.order_id
            LEFT JOIN olist_products_dataset AS p ON p.product_id = i.product_id
            LEFT JOIN product_category_name_translation AS t
                ON t.product_category_name = p.product_category_name
            WHERE {scope} AND {item_scope}
              AND o.order_purchase_timestamp IS NOT NULL
            GROUP BY period
            ORDER BY period""",
        [*scope_params, *item_params],
        database_path,
    )


def order_status_distribution(
    filters: DashboardFilters,
    database_path: str | None = None,
) -> pd.DataFrame:
    scope, params = _order_scope(filters)
    return _run(
        f"""SELECT o.order_status, COUNT(DISTINCT o.order_id) AS order_count
            FROM olist_orders_dataset AS o
            WHERE {scope}
            GROUP BY o.order_status
            ORDER BY order_count DESC""",
        params,
        database_path,
    )


def sales_by_state(
    filters: DashboardFilters,
    database_path: str | None = None,
) -> pd.DataFrame:
    scope, scope_params = _order_scope(filters)
    item_scope, item_params = _item_category_scope(filters)
    return _run(
        f"""SELECT c.customer_state AS state,
                   COUNT(DISTINCT o.order_id) AS all_status_orders,
                   COUNT(DISTINCT CASE WHEN o.order_status = 'delivered'
                       THEN o.order_id END) AS delivered_orders,
                   COALESCE(SUM(CASE WHEN o.order_status = 'delivered'
                       THEN COALESCE(i.price, 0) ELSE 0 END), 0) AS delivered_item_revenue,
                   COALESCE(SUM(CASE WHEN o.order_status = 'delivered'
                       THEN COALESCE(i.freight_value, 0) ELSE 0 END), 0) AS delivered_freight,
                   COALESCE(SUM(CASE WHEN o.order_status = 'delivered'
                       THEN COALESCE(i.price, 0) + COALESCE(i.freight_value, 0)
                       ELSE 0 END), 0) AS delivered_total_value,
                   COALESCE(SUM(COALESCE(i.price, 0) + COALESCE(i.freight_value, 0)),
                       0) AS all_status_item_value
            FROM olist_orders_dataset AS o
            LEFT JOIN olist_customers_dataset AS c ON c.customer_id = o.customer_id
            LEFT JOIN olist_order_items_dataset AS i ON i.order_id = o.order_id
            LEFT JOIN olist_products_dataset AS p ON p.product_id = i.product_id
            LEFT JOIN product_category_name_translation AS t
                ON t.product_category_name = p.product_category_name
            WHERE {scope} AND {item_scope}
            GROUP BY c.customer_state
            ORDER BY delivered_item_revenue DESC""",
        [*scope_params, *item_params],
        database_path,
    )


def revenue_freight(
    filters: DashboardFilters,
    database_path: str | None = None,
) -> pd.DataFrame:
    scope, scope_params = _order_scope(filters)
    item_scope, item_params = _item_category_scope(filters)
    return _run(
        f"""SELECT COALESCE(SUM(COALESCE(i.price, 0)), 0) AS delivered_item_revenue,
                   COALESCE(SUM(COALESCE(i.freight_value, 0)), 0) AS delivered_freight
            FROM olist_orders_dataset AS o
            JOIN olist_order_items_dataset AS i ON i.order_id = o.order_id
            LEFT JOIN olist_products_dataset AS p ON p.product_id = i.product_id
            LEFT JOIN product_category_name_translation AS t
                ON t.product_category_name = p.product_category_name
            WHERE {scope} AND o.order_status = 'delivered' AND {item_scope}""",
        [*scope_params, *item_params],
        database_path,
    )


def category_performance(
    filters: DashboardFilters,
    category: str | None = None,
    database_path: str | None = None,
) -> pd.DataFrame:
    scope, scope_params = _order_scope(filters)
    item_scope, item_params = _item_category_scope(filters)
    sql = f"""SELECT {_category_expression()} AS category,
                     COUNT(*) AS all_status_items,
                     COUNT(DISTINCT o.order_id) AS all_status_orders,
                     COUNT(DISTINCT i.product_id) AS products,
                     COALESCE(SUM(COALESCE(i.price, 0) + COALESCE(i.freight_value, 0)),
                         0) AS all_status_item_value,
                     COALESCE(SUM(CASE WHEN o.order_status = 'delivered'
                         THEN COALESCE(i.price, 0) ELSE 0 END), 0) AS delivered_item_revenue,
                     COALESCE(SUM(CASE WHEN o.order_status = 'delivered'
                         THEN COALESCE(i.freight_value, 0) ELSE 0 END), 0) AS delivered_freight,
                     COALESCE(SUM(CASE WHEN o.order_status = 'delivered'
                         THEN COALESCE(i.price, 0) + COALESCE(i.freight_value, 0)
                         ELSE 0 END), 0) AS delivered_total_value,
                     COUNT(DISTINCT CASE WHEN o.order_status = 'delivered'
                         THEN o.order_id END) AS delivered_orders
              FROM olist_orders_dataset AS o
              JOIN olist_order_items_dataset AS i ON i.order_id = o.order_id
              LEFT JOIN olist_products_dataset AS p ON p.product_id = i.product_id
              LEFT JOIN product_category_name_translation AS t
                  ON t.product_category_name = p.product_category_name
              WHERE {scope} AND {item_scope}"""
    params = [*scope_params, *item_params]
    if category:
        sql += " AND " + _category_expression() + " = ?"
        params.append(category)
    sql += " GROUP BY category ORDER BY delivered_item_revenue DESC"
    return _run(sql, params, database_path)


def product_performance(
    filters: DashboardFilters,
    category: str | None = None,
    limit: int = 50,
    database_path: str | None = None,
) -> pd.DataFrame:
    scope, scope_params = _order_scope(filters)
    item_scope, item_params = _item_category_scope(filters)
    sql = f"""SELECT i.product_id, {_category_expression()} AS category,
                   COUNT(*) AS items_sold,
                   COUNT(DISTINCT o.order_id) AS orders,
                   COALESCE(SUM(CASE WHEN o.order_status = 'delivered'
                       THEN COALESCE(i.price, 0) ELSE 0 END), 0) AS delivered_item_revenue,
                   COALESCE(SUM(CASE WHEN o.order_status = 'delivered'
                       THEN COALESCE(i.freight_value, 0) ELSE 0 END), 0) AS delivered_freight
            FROM olist_orders_dataset AS o
            JOIN olist_order_items_dataset AS i ON i.order_id = o.order_id
            LEFT JOIN olist_products_dataset AS p ON p.product_id = i.product_id
            LEFT JOIN product_category_name_translation AS t
                ON t.product_category_name = p.product_category_name
            WHERE {scope} AND {item_scope}
            """
    params: list[object] = [*scope_params, *item_params]
    if category:
        sql += " AND " + _category_expression() + " = ?"
        params.append(category)
    sql += """ GROUP BY i.product_id, category
               ORDER BY delivered_item_revenue DESC, items_sold DESC
               LIMIT ?"""
    params.append(limit)
    return _run(sql, params, database_path)


def customer_distribution(
    filters: DashboardFilters,
    database_path: str | None = None,
) -> pd.DataFrame:
    scope, params = _order_scope(filters)
    return _run(
        f"""SELECT c.customer_state AS state,
                   COUNT(DISTINCT c.customer_unique_id) AS customers,
                   COUNT(DISTINCT o.order_id) AS orders
            FROM olist_orders_dataset AS o
            JOIN olist_customers_dataset AS c ON c.customer_id = o.customer_id
            WHERE {scope}
            GROUP BY c.customer_state
            ORDER BY customers DESC""",
        params,
        database_path,
    )


def customer_order_patterns(
    filters: DashboardFilters,
    database_path: str | None = None,
) -> pd.DataFrame:
    scope, params = _order_scope(filters)
    return _run(
        f"""WITH per_customer AS (
                SELECT c.customer_unique_id, COUNT(DISTINCT o.order_id) AS order_count
                FROM olist_orders_dataset AS o
                JOIN olist_customers_dataset AS c ON c.customer_id = o.customer_id
                WHERE {scope} AND c.customer_unique_id IS NOT NULL
                GROUP BY c.customer_unique_id
            )
            SELECT order_count, COUNT(*) AS customers
            FROM per_customer
            GROUP BY order_count
            ORDER BY order_count""",
        params,
        database_path,
    )


def review_scores(
    filters: DashboardFilters,
    database_path: str | None = None,
) -> pd.DataFrame:
    scope, params = _order_scope(filters)
    return _run(
        f"""SELECT r.review_score, COUNT(*) AS review_count
            FROM olist_order_reviews_dataset AS r
            JOIN olist_orders_dataset AS o ON o.order_id = r.order_id
            WHERE {scope} AND r.review_score IS NOT NULL
            GROUP BY r.review_score
            ORDER BY r.review_score""",
        params,
        database_path,
    )


def payment_types(
    filters: DashboardFilters,
    database_path: str | None = None,
) -> pd.DataFrame:
    scope, params = _order_scope(filters)
    return _run(
        f"""SELECT p.payment_type, COUNT(*) AS payment_count,
                   COUNT(DISTINCT p.order_id) AS order_count,
                   COALESCE(SUM(p.payment_value), 0) AS payment_value
            FROM olist_order_payments_dataset AS p
            JOIN olist_orders_dataset AS o ON o.order_id = p.order_id
            WHERE {scope}
            GROUP BY p.payment_type
            ORDER BY payment_value DESC""",
        params,
        database_path,
    )


def payment_installments(
    filters: DashboardFilters,
    database_path: str | None = None,
) -> pd.DataFrame:
    scope, params = _order_scope(filters)
    return _run(
        f"""SELECT p.payment_installments AS installments,
                   COUNT(*) AS payment_records,
                   COUNT(DISTINCT p.order_id) AS orders,
                   COALESCE(SUM(p.payment_value), 0) AS payment_value
            FROM olist_order_payments_dataset AS p
            JOIN olist_orders_dataset AS o ON o.order_id = p.order_id
            WHERE {scope}
            GROUP BY p.payment_installments
            ORDER BY p.payment_installments""",
        params,
        database_path,
    )


def delivery_performance(
    filters: DashboardFilters,
    database_path: str | None = None,
) -> pd.DataFrame:
    scope, params = _order_scope(filters)
    return _run(
        f"""WITH delivered AS (
                SELECT julianday(o.order_delivered_customer_date)
                           - julianday(o.order_purchase_timestamp) AS delivery_days,
                       julianday(o.order_delivered_customer_date)
                           - julianday(o.order_estimated_delivery_date) AS days_late
                FROM olist_orders_dataset AS o
                WHERE {scope}
                  AND o.order_status = 'delivered'
                  AND o.order_delivered_customer_date IS NOT NULL
                  AND o.order_purchase_timestamp IS NOT NULL
            ),
            bucketed AS (
                SELECT CASE
                           WHEN delivery_days < 0 THEN 'Negative duration'
                           WHEN delivery_days < 4 THEN '0-3 days'
                           WHEN delivery_days < 8 THEN '4-7 days'
                           WHEN delivery_days < 15 THEN '8-14 days'
                           WHEN delivery_days < 31 THEN '15-30 days'
                           ELSE '31+ days'
                       END AS delivery_bucket,
                       CASE
                           WHEN delivery_days < 0 THEN 0
                           WHEN delivery_days < 4 THEN 1
                           WHEN delivery_days < 8 THEN 2
                           WHEN delivery_days < 15 THEN 3
                           WHEN delivery_days < 31 THEN 4
                           ELSE 5
                       END AS bucket_order,
                       delivery_days, days_late
                FROM delivered
            ),
            distribution AS (
                SELECT delivery_bucket, bucket_order, COUNT(*) AS orders
                FROM bucketed
                GROUP BY delivery_bucket, bucket_order
            ),
            summary AS (
                SELECT COUNT(*) AS delivered_orders,
                       AVG(delivery_days) AS average_delivery_days,
                       SUM(CASE WHEN days_late > 0 THEN 1 ELSE 0 END)
                           * 100.0 / NULLIF(COUNT(days_late), 0) AS delayed_pct,
                       AVG(CASE WHEN days_late > 0 THEN days_late END)
                           AS average_days_late
                FROM delivered
            )
            SELECT d.delivery_bucket, d.orders, s.delivered_orders,
                   s.average_delivery_days, s.delayed_pct, s.average_days_late
            FROM distribution AS d CROSS JOIN summary AS s
            ORDER BY d.bucket_order""",
        params,
        database_path,
    )


def payment_reconciliation(
    filters: DashboardFilters,
    database_path: str | None = None,
) -> pd.DataFrame:
    scope, params = _order_scope(filters)
    return _run(
        f"""WITH selected_orders AS (
                SELECT o.order_id FROM olist_orders_dataset AS o WHERE {scope}
            ),
            payments AS (
                SELECT SUM(p.payment_value) AS payment_value
                FROM olist_order_payments_dataset AS p
                JOIN selected_orders AS so ON so.order_id = p.order_id
            ),
            items AS (
                SELECT SUM(i.price) AS item_price, SUM(i.freight_value) AS freight
                FROM olist_order_items_dataset AS i
                JOIN selected_orders AS so ON so.order_id = i.order_id
            )
            SELECT COALESCE(payments.payment_value, 0) AS payment_value,
                   COALESCE(items.item_price, 0) AS item_price,
                   COALESCE(items.freight, 0) AS freight,
                   COALESCE(items.item_price, 0) + COALESCE(items.freight, 0)
                       AS item_price_plus_freight,
                   COALESCE(payments.payment_value, 0)
                       - COALESCE(items.item_price, 0) - COALESCE(items.freight, 0)
                       AS difference
            FROM payments CROSS JOIN items""",
        params,
        database_path,
    )


def order_search_counts(
    filters: DashboardFilters,
    search_term: str = "",
    database_path: str | None = None,
) -> dict[str, int]:
    scope, scope_params = _order_scope(filters)
    row = _run(
        f"""SELECT COUNT(DISTINCT o.order_id) AS matching_orders,
                   COUNT(DISTINCT CASE WHEN o.order_status = 'delivered'
                       THEN o.order_id END) AS delivered_orders,
                   COUNT(DISTINCT c.customer_unique_id) AS customers
            FROM olist_orders_dataset AS o
            LEFT JOIN olist_customers_dataset AS c ON c.customer_id = o.customer_id
            WHERE {scope} AND o.order_id LIKE ?""",
        [*scope_params, f"%{search_term.strip()}%"],
        database_path,
    ).iloc[0]
    return {
        "matching_orders": int(row["matching_orders"]),
        "delivered_orders": int(row["delivered_orders"]),
        "customers": int(row["customers"]),
    }


def search_orders(
    filters: DashboardFilters,
    search_term: str = "",
    limit: int = 500,
    database_path: str | None = None,
) -> pd.DataFrame:
    scope, scope_params = _order_scope(filters)
    item_scope, item_params = _item_category_scope(filters)
    sql = f"""WITH selected_orders AS (
                  SELECT o.order_id, o.customer_id, o.order_status,
                         o.order_purchase_timestamp, o.order_approved_at,
                         o.order_delivered_customer_date, o.order_estimated_delivery_date
                  FROM olist_orders_dataset AS o
                  WHERE {scope}
              ),
              item_summary AS (
                  SELECT i.order_id, COUNT(*) AS item_count,
                         SUM(COALESCE(i.price, 0)) AS item_price,
                         SUM(COALESCE(i.freight_value, 0)) AS freight,
                         GROUP_CONCAT(DISTINCT {_category_expression()}) AS categories,
                         GROUP_CONCAT(DISTINCT i.product_id) AS product_ids
                  FROM olist_order_items_dataset AS i
                  LEFT JOIN olist_products_dataset AS p ON p.product_id = i.product_id
                  LEFT JOIN product_category_name_translation AS t
                      ON t.product_category_name = p.product_category_name
                  JOIN selected_orders AS so ON so.order_id = i.order_id
                  WHERE {item_scope}
                  GROUP BY i.order_id
              ),
              payment_summary AS (
                  SELECT p.order_id, SUM(p.payment_value) AS payment_value,
                         GROUP_CONCAT(DISTINCT p.payment_type) AS payment_types,
                         MAX(p.payment_installments) AS max_installments
                  FROM olist_order_payments_dataset AS p
                  JOIN selected_orders AS so ON so.order_id = p.order_id
                  GROUP BY p.order_id
              ),
              review_summary AS (
                  SELECT r.order_id, AVG(r.review_score) AS average_review_score,
                         COUNT(*) AS review_count
                  FROM olist_order_reviews_dataset AS r
                  JOIN selected_orders AS so ON so.order_id = r.order_id
                  GROUP BY r.order_id
              )
              SELECT so.order_id, so.order_purchase_timestamp, so.order_status,
                     c.customer_unique_id, c.customer_city, c.customer_state,
                     item_summary.item_count, item_summary.categories,
                     item_summary.product_ids, item_summary.item_price,
                     item_summary.freight,
                     item_summary.item_price + item_summary.freight AS item_total_value,
                     payment_summary.payment_value, payment_summary.payment_types,
                     payment_summary.max_installments,
                     review_summary.average_review_score, review_summary.review_count,
                     so.order_delivered_customer_date, so.order_estimated_delivery_date,
                     julianday(so.order_delivered_customer_date)
                         - julianday(so.order_purchase_timestamp) AS delivery_days,
                     julianday(so.order_delivered_customer_date)
                         - julianday(so.order_estimated_delivery_date) AS days_late
              FROM selected_orders AS so
              LEFT JOIN olist_customers_dataset AS c ON c.customer_id = so.customer_id
              LEFT JOIN item_summary ON item_summary.order_id = so.order_id
              LEFT JOIN payment_summary ON payment_summary.order_id = so.order_id
              LEFT JOIN review_summary ON review_summary.order_id = so.order_id
              WHERE so.order_id LIKE ?
              ORDER BY so.order_purchase_timestamp DESC
              LIMIT ?"""
    params = [
        *scope_params,
        *item_params,
        f"%{search_term.strip()}%",
        limit,
    ]
    return _run(sql, params, database_path)
