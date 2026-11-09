import os
import subprocess
import sqlite3
import sys
from pathlib import Path

import pytest

from dashboard.components import format_table
from dashboard.database import connect_read_only, read_query
from dashboard.queries import (
    DashboardFilters,
    category_performance,
    customer_distribution,
    customer_order_patterns,
    delivery_performance,
    get_filter_options,
    get_kpis,
    order_search_counts,
    order_status_distribution,
    payment_installments,
    payment_reconciliation,
    payment_types,
    product_performance,
    review_scores,
    sales_by_state,
    sales_trend,
    search_orders,
)


@pytest.fixture
def dashboard_database(tmp_path: Path) -> Path:
    path = tmp_path / "dashboard.sqlite"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE olist_customers_dataset (
            customer_id TEXT, customer_unique_id TEXT, customer_city TEXT,
            customer_state TEXT
        );
        CREATE TABLE olist_orders_dataset (
            order_id TEXT, customer_id TEXT, order_status TEXT,
            order_purchase_timestamp TIMESTAMP, order_approved_at TIMESTAMP,
            order_delivered_customer_date TIMESTAMP,
            order_estimated_delivery_date TIMESTAMP
        );
        CREATE TABLE olist_order_items_dataset (
            order_id TEXT, order_item_id INTEGER, product_id TEXT,
            price REAL, freight_value REAL
        );
        CREATE TABLE olist_products_dataset (
            product_id TEXT, product_category_name TEXT
        );
        CREATE TABLE product_category_name_translation (
            product_category_name TEXT, product_category_name_english TEXT
        );
        CREATE TABLE olist_order_payments_dataset (
            order_id TEXT, payment_type TEXT, payment_installments INTEGER,
            payment_value REAL
        );
        CREATE TABLE olist_order_reviews_dataset (
            review_id TEXT, order_id TEXT, review_score INTEGER
        );
        INSERT INTO olist_customers_dataset VALUES
            ('c1', 'u1', 'Sao Paulo', 'SP'),
            ('c2', 'u1', 'Sao Paulo', 'SP'),
            ('c3', 'u2', 'Rio', 'RJ');
        INSERT INTO olist_orders_dataset VALUES
            ('order-001', 'c1', 'delivered', '2017-01-02 10:00:00',
             '2017-01-02', '2017-01-05', '2017-01-08'),
            ('order-002', 'c1', 'canceled', '2017-01-03 10:00:00',
             NULL, NULL, '2017-01-10'),
            ('order-003', 'c2', 'delivered', '2017-02-01 10:00:00',
             '2017-02-01', '2017-02-06', '2017-02-05'),
            ('order-004', 'c3', 'delivered', NULL,
             NULL, '2017-03-04', '2017-03-08');
        INSERT INTO olist_order_items_dataset VALUES
            ('order-001', 1, 'p-book', 100, 10),
            ('order-001', 2, 'p-toy', 10, 2),
            ('order-002', 1, 'p-toy', 40, 5),
            ('order-003', 1, 'p-book', 50, 5),
            ('order-004', 1, 'p-unknown', 25, 2);
        INSERT INTO olist_products_dataset VALUES
            ('p-book', 'books'), ('p-toy', 'toys'), ('p-unknown', NULL);
        INSERT INTO product_category_name_translation VALUES
            ('books', 'Books'), ('toys', 'Toys');
        INSERT INTO olist_order_payments_dataset VALUES
            ('order-001', 'credit_card', 2, 70),
            ('order-001', 'voucher', 1, 52),
            ('order-002', 'credit_card', 1, 45),
            ('order-003', 'debit_card', 1, 55),
            ('order-004', 'credit_card', 3, 27);
        INSERT INTO olist_order_reviews_dataset VALUES
            ('review-1', 'order-001', 5),
            ('review-2', 'order-003', 3),
            ('review-3', 'order-003', 4);
        """
    )
    connection.commit()
    connection.close()
    read_query.clear()
    return path


def test_read_only_connection_and_missing_database(dashboard_database: Path, tmp_path: Path) -> None:
    connection = connect_read_only(dashboard_database)
    assert connection.execute("PRAGMA query_only").fetchone()[0] == 1
    with pytest.raises(sqlite3.OperationalError):
        connection.execute("INSERT INTO olist_orders_dataset VALUES ('bad')")
    connection.close()
    with pytest.raises(FileNotFoundError, match="SQLite database not found"):
        connect_read_only(tmp_path / "missing.sqlite")


def test_streamlit_entrypoint_imports_from_outside_project_root(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    script = (
        "import runpy, sys\n"
        f"root = {str(project_root)!r}\n"
        "sys.path = [entry for entry in sys.path "
        "if not entry or __import__('pathlib').Path(entry).resolve() != "
        "__import__('pathlib').Path(root)]\n"
        "runpy.run_path(root + '/dashboard/app.py', run_name='__main__')\n"
    )
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_filter_options_and_global_filters(dashboard_database: Path) -> None:
    options = get_filter_options(str(dashboard_database))
    assert options["min_date"] == "2017-01-02"
    assert options["max_date"] == "2017-02-01"
    assert options["states"] == ["RJ", "SP"]
    assert options["categories"] == ["Books", "Toys", "Unknown"]

    filters = DashboardFilters(
        start_date="2017-01-01",
        end_date="2017-01-31",
        states=("SP",),
        categories=("Books",),
        statuses=("delivered",),
    )
    metrics = get_kpis(filters, str(dashboard_database))
    assert metrics["orders"] == 1
    assert metrics["delivered_orders"] == 1
    assert metrics["customers"] == 1
    assert metrics["delivered_revenue"] == 100
    assert metrics["delivered_freight"] == 10
    assert metrics["average_order_value"] == 100


def test_order_search_counts_include_all_matching_rows_and_respect_filters(
    dashboard_database: Path,
) -> None:
    counts = order_search_counts(DashboardFilters(), database_path=str(dashboard_database))
    limited_rows = search_orders(
        DashboardFilters(),
        limit=2,
        database_path=str(dashboard_database),
    )
    assert len(limited_rows) == 2
    assert counts == {
        "matching_orders": 4,
        "delivered_orders": 3,
        "customers": 2,
    }

    filtered_counts = order_search_counts(
        DashboardFilters(categories=("Books",)),
        search_term="003",
        database_path=str(dashboard_database),
    )
    assert filtered_counts == {
        "matching_orders": 1,
        "delivered_orders": 1,
        "customers": 1,
    }


def test_delivered_revenue_and_all_status_value_are_separate(
    dashboard_database: Path,
) -> None:
    metrics = get_kpis(DashboardFilters(), str(dashboard_database))
    assert metrics["orders"] == 4
    assert metrics["delivered_orders"] == 3
    assert metrics["customers"] == 2
    assert metrics["delivered_revenue"] == 185
    assert metrics["delivered_freight"] == 19
    assert metrics["average_order_value"] == pytest.approx(185 / 3)

    monthly = sales_trend(DashboardFilters(), "month", str(dashboard_database))
    assert monthly["period"].tolist() == ["2017-01", "2017-02"]
    assert monthly["delivered_item_revenue"].tolist() == [110, 50]
    assert monthly["all_status_item_value"].tolist() == [167, 55]
    quarterly = sales_trend(DashboardFilters(), "quarter", str(dashboard_database))
    yearly = sales_trend(DashboardFilters(), "year", str(dashboard_database))
    assert quarterly["period"].tolist() == ["2017-Q1"]
    assert yearly["period"].tolist() == ["2017"]
    with pytest.raises(ValueError, match="Unsupported sales grain"):
        sales_trend(DashboardFilters(), "weekly", str(dashboard_database))


def test_sales_trend_keeps_final_incomplete_period(tmp_path: Path) -> None:
    path = tmp_path / "incomplete-month.sqlite"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE olist_orders_dataset (
            order_id TEXT, customer_id TEXT, order_status TEXT,
            order_purchase_timestamp TIMESTAMP, order_approved_at TIMESTAMP,
            order_delivered_customer_date TIMESTAMP, order_estimated_delivery_date TIMESTAMP
        );
        CREATE TABLE olist_order_items_dataset (
            order_id TEXT, order_item_id INTEGER, product_id TEXT,
            price REAL, freight_value REAL
        );
        CREATE TABLE olist_products_dataset (
            product_id TEXT, product_category_name TEXT
        );
        CREATE TABLE product_category_name_translation (
            product_category_name TEXT, product_category_name_english TEXT
        );
        CREATE TABLE olist_customers_dataset (
            customer_id TEXT, customer_unique_id TEXT, customer_city TEXT,
            customer_state TEXT
        );
        """
    )
    connection.execute(
        "INSERT INTO olist_orders_dataset VALUES (?, ?, ?, ?, NULL, NULL, NULL)",
        ("order-100", "customer-1", "created", "2017-03-18 09:00:00"),
    )
    connection.execute(
        "INSERT INTO olist_order_items_dataset VALUES (?, ?, ?, ?, ?)",
        ("order-100", 1, "product-1", 42.5, 5.0),
    )
    connection.execute(
        "INSERT INTO olist_products_dataset VALUES (?, ?)",
        ("product-1", "books"),
    )
    connection.execute(
        "INSERT INTO product_category_name_translation VALUES (?, ?)",
        ("books", "Books"),
    )
    connection.execute(
        "INSERT INTO olist_customers_dataset VALUES (?, ?, ?, ?)",
        ("customer-1", "customer-unique-1", "City", "SP"),
    )
    connection.commit()
    connection.close()

    trend = sales_trend(DashboardFilters(start_date="2017-03-01", end_date="2017-03-31"), "month", str(path))
    assert trend["period"].tolist() == ["2017-03"]
    assert trend["delivered_orders"].tolist() == [0]
    assert trend["all_status_item_value"].tolist() == [47.5]
    assert trend["delivered_item_revenue"].tolist() == [0]


def test_queries_handle_empty_results_and_keep_payment_grain(
    dashboard_database: Path,
) -> None:
    no_matches = DashboardFilters(start_date="2020-01-01", end_date="2020-01-31")
    assert get_kpis(no_matches, str(dashboard_database))["delivered_revenue"] == 0
    assert sales_trend(no_matches, database_path=str(dashboard_database)).empty
    assert search_orders(no_matches, database_path=str(dashboard_database)).empty

    filters = DashboardFilters(categories=("Books",))
    payments = payment_types(filters, str(dashboard_database))
    assert payments["payment_value"].sum() == 177
    recon = payment_reconciliation(filters, str(dashboard_database)).iloc[0]
    assert recon["payment_value"] == 177
    assert recon["item_price_plus_freight"] == 177

    score_rows = review_scores(DashboardFilters(), str(dashboard_database))
    assert score_rows["review_count"].sum() == 3
    patterns = customer_order_patterns(DashboardFilters(), str(dashboard_database))
    assert patterns.set_index("order_count").loc[3, "customers"] == 1


def test_search_is_parameterized_and_order_details_do_not_multiply_rows(
    dashboard_database: Path,
) -> None:
    results = search_orders(
        DashboardFilters(categories=("Books",)),
        search_term="order-001",
        database_path=str(dashboard_database),
    )
    assert len(results) == 1
    assert results.iloc[0]["item_count"] == 1
    assert results.iloc[0]["item_price"] == 100
    assert results.iloc[0]["payment_value"] == 122
    assert results.iloc[0]["review_count"] == 1

    assert search_orders(
        DashboardFilters(),
        search_term="%' OR 1=1 --",
        database_path=str(dashboard_database),
    ).empty
    assert len(search_orders(DashboardFilters(), database_path=str(dashboard_database))) == 4


def test_cancelled_order_table_formats_missing_numeric_values(
    dashboard_database: Path,
) -> None:
    orders = search_orders(
        DashboardFilters(),
        search_term="order-002",
        database_path=str(dashboard_database),
    )
    display_orders = orders.replace("None", "—")

    rendered = format_table(
        display_orders,
        {"item_count": "Items", "review_count": "Review records"},
        integer_columns=("item_count", "review_count"),
    ).to_html()

    assert "canceled" in rendered
    assert "—" in rendered


def test_remaining_dashboard_aggregations_execute(dashboard_database: Path) -> None:
    filters = DashboardFilters()
    path = str(dashboard_database)
    assert len(order_status_distribution(filters, path)) == 2
    assert not sales_by_state(filters, path).empty
    assert not category_performance(filters, database_path=path).empty
    assert not product_performance(filters, database_path=path).empty
    assert not customer_distribution(filters, path).empty
    assert not payment_installments(filters, path).empty
    delivery = delivery_performance(filters, path)
    assert delivery["delivered_orders"].iloc[0] == 2
    assert delivery["delayed_pct"].iloc[0] == 50
