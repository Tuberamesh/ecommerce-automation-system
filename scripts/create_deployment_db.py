from pathlib import Path
import sqlite3
import uuid

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "database" / "ecommerce.db"
DESTINATION = ROOT / "database" / "deployment_ecommerce.db"

if not SOURCE.is_file():
    raise FileNotFoundError(f"Source database not found: {SOURCE}")

if DESTINATION.exists():
    raise FileExistsError(
        f"{DESTINATION} already exists. "
        "Move or rename it before creating a new copy."
    )


def make_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex}"


def build_mapping(values, prefix):
    return {
        value: make_id(prefix)
        for value in values
        if value is not None
    }


source = sqlite3.connect(f"{SOURCE.as_uri()}?mode=ro", uri=True)
source.row_factory = sqlite3.Row

destination = sqlite3.connect(DESTINATION)

try:
    # Read source records.
    orders = source.execute(
        "SELECT * FROM olist_orders_dataset"
    ).fetchall()

    customers = source.execute(
        "SELECT * FROM olist_customers_dataset"
    ).fetchall()

    items = source.execute(
        "SELECT * FROM olist_order_items_dataset"
    ).fetchall()

    products = source.execute(
        "SELECT * FROM olist_products_dataset"
    ).fetchall()

    categories = source.execute(
        "SELECT * FROM product_category_name_translation"
    ).fetchall()

    payments = source.execute(
        "SELECT * FROM olist_order_payments_dataset"
    ).fetchall()

    reviews = source.execute(
        "SELECT * FROM olist_order_reviews_dataset"
    ).fetchall()

    # Build consistent random ID mappings across related tables.
    order_values = {
        row["order_id"] for row in orders + items + payments + reviews
    }
    customer_values = {
        row["customer_id"] for row in orders + customers
    }
    unique_customer_values = {
        row["customer_unique_id"] for row in customers
    }
    product_values = {
        row["product_id"] for row in products + items
    }

    order_map = build_mapping(order_values, "order")
    customer_map = build_mapping(customer_values, "customer")
    unique_customer_map = build_mapping(
        unique_customer_values, "customer"
    )
    product_map = build_mapping(product_values, "product")

    # Create minimal dashboard-compatible tables.
    destination.executescript("""
        CREATE TABLE olist_orders_dataset (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT,
            order_status TEXT,
            order_purchase_timestamp TEXT,
            order_approved_at TEXT,
            order_delivered_customer_date TEXT,
            order_estimated_delivery_date TEXT
        );

        CREATE TABLE olist_customers_dataset (
            customer_id TEXT PRIMARY KEY,
            customer_unique_id TEXT,
            customer_state TEXT
        );

        CREATE TABLE olist_order_items_dataset (
            order_id TEXT,
            order_item_id INTEGER,
            product_id TEXT,
            price REAL,
            freight_value REAL
        );

        CREATE TABLE olist_products_dataset (
            product_id TEXT PRIMARY KEY,
            product_category_name TEXT
        );

        CREATE TABLE product_category_name_translation (
            product_category_name TEXT,
            product_category_name_english TEXT
        );

        CREATE TABLE olist_order_payments_dataset (
            order_id TEXT,
            payment_sequential INTEGER,
            payment_type TEXT,
            payment_installments INTEGER,
            payment_value REAL
        );

        CREATE TABLE olist_order_reviews_dataset (
            order_id TEXT,
            review_score INTEGER
        );

        CREATE INDEX idx_orders_purchase
            ON olist_orders_dataset(order_purchase_timestamp);

        CREATE INDEX idx_orders_customer
            ON olist_orders_dataset(customer_id);

        CREATE INDEX idx_items_order
            ON olist_order_items_dataset(order_id);

        CREATE INDEX idx_items_product
            ON olist_order_items_dataset(product_id);

        CREATE INDEX idx_payments_order
            ON olist_order_payments_dataset(order_id);

        CREATE INDEX idx_reviews_order
            ON olist_order_reviews_dataset(order_id);
    """)

    # Insert orders.
    destination.executemany("""
        INSERT INTO olist_orders_dataset VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [
        (
            order_map.get(row["order_id"]),
            customer_map.get(row["customer_id"]),
            row["order_status"],
            row["order_purchase_timestamp"],
            row["order_approved_at"],
            row["order_delivered_customer_date"],
            row["order_estimated_delivery_date"],
        )
        for row in orders
    ])

    # Insert customers without city or postal information.
    destination.executemany("""
        INSERT INTO olist_customers_dataset VALUES (?, ?, ?)
    """, [
        (
            customer_map.get(row["customer_id"]),
            unique_customer_map.get(row["customer_unique_id"]),
            row["customer_state"],
        )
        for row in customers
    ])

    # Insert order items without seller IDs or shipping-limit dates.
    destination.executemany("""
        INSERT INTO olist_order_items_dataset VALUES (?, ?, ?, ?, ?)
    """, [
        (
            order_map.get(row["order_id"]),
            row["order_item_id"],
            product_map.get(row["product_id"]),
            row["price"],
            row["freight_value"],
        )
        for row in items
    ])

    # Insert products without physical dimensions.
    destination.executemany("""
        INSERT INTO olist_products_dataset VALUES (?, ?)
    """, [
        (
            product_map.get(row["product_id"]),
            row["product_category_name"],
        )
        for row in products
    ])

    destination.executemany("""
        INSERT INTO product_category_name_translation VALUES (?, ?)
    """, [
        (
            row["product_category_name"],
            row["product_category_name_english"],
        )
        for row in categories
    ])

    # Insert payment records without changing financial values.
    destination.executemany("""
        INSERT INTO olist_order_payments_dataset VALUES (?, ?, ?, ?, ?)
    """, [
        (
            order_map.get(row["order_id"]),
            row["payment_sequential"],
            row["payment_type"],
            row["payment_installments"],
            row["payment_value"],
        )
        for row in payments
    ])

    # Keep review scores and order relationships; omit review text and IDs.
    destination.executemany("""
        INSERT INTO olist_order_reviews_dataset VALUES (?, ?)
    """, [
        (
            order_map.get(row["order_id"]),
            row["review_score"],
        )
        for row in reviews
    ])

    destination.commit()

    # Validate row counts.
    expected_counts = {
        "olist_orders_dataset": len(orders),
        "olist_customers_dataset": len(customers),
        "olist_order_items_dataset": len(items),
        "olist_products_dataset": len(products),
        "product_category_name_translation": len(categories),
        "olist_order_payments_dataset": len(payments),
        "olist_order_reviews_dataset": len(reviews),
    }

    print("\nROW COUNT VALIDATION")
    for table, expected in expected_counts.items():
        actual = destination.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        status = "PASS" if actual == expected else "FAIL"
        print(f"{status}: {table}: {actual:,} rows (source: {expected:,})")

        if actual != expected:
            raise RuntimeError(f"Row count mismatch: {table}")

    # Validate that no order references are broken.
    checks = {
        "items without matching orders": """
            SELECT COUNT(*)
            FROM olist_order_items_dataset i
            LEFT JOIN olist_orders_dataset o USING (order_id)
            WHERE o.order_id IS NULL
        """,
        "payments without matching orders": """
            SELECT COUNT(*)
            FROM olist_order_payments_dataset p
            LEFT JOIN olist_orders_dataset o USING (order_id)
            WHERE o.order_id IS NULL
        """,
        "reviews without matching orders": """
            SELECT COUNT(*)
            FROM olist_order_reviews_dataset r
            LEFT JOIN olist_orders_dataset o USING (order_id)
            WHERE o.order_id IS NULL
        """,
    }

    print("\nRELATIONSHIP VALIDATION")
    for label, query in checks.items():
        count = destination.execute(query).fetchone()[0]
        print(f"{'PASS' if count == 0 else 'FAIL'}: {label}: {count}")

        if count:
            raise RuntimeError(f"Relationship validation failed: {label}")

    # Check that excluded fields are absent.
    forbidden_columns = {
        "customer_city",
        "customer_zip_code_prefix",
        "seller_id",
        "review_id",
        "review_comment_title",
        "review_comment_message",
        "review_creation_date",
        "review_answer_timestamp",
    }

    found = set()
    for (table,) in destination.execute("""
        SELECT name FROM sqlite_master WHERE type = 'table'
    """):
        columns = {
            row[1] for row in destination.execute(
                f"PRAGMA table_info({table})"
            )
        }
        found.update(columns & forbidden_columns)

    if found:
        raise RuntimeError(f"Excluded columns still present: {found}")

    print("\nPRIVACY-FIELD CHECK: PASS")
    print("No excluded location, seller, or review-text columns found.")

    integrity = destination.execute("PRAGMA integrity_check").fetchone()[0]
    print(f"DATABASE INTEGRITY: {integrity}")

    if integrity != "ok":
        raise RuntimeError("SQLite integrity check failed.")

finally:
    destination.close()
    source.close()

print(f"\nCreated: {DESTINATION}")
print(f"Size: {DESTINATION.stat().st_size / (1024 * 1024):.2f} MB")
print("Original database was opened read-only and was not modified.")
