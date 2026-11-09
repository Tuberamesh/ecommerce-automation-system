import logging
import sqlite3
from pathlib import Path

import pandas as pd


logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "database" / "ecommerce.db"


def write_database(
    datasets: dict[str, pd.DataFrame],
    order_item_fact: pd.DataFrame,
    database_path: Path | str = DEFAULT_DATABASE_PATH,
) -> Path:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    try:
        with connection:
            for file_name, df in datasets.items():
                table_name = Path(file_name).stem
                df.to_sql(table_name, connection, if_exists="replace", index=False)
                logger.info("Wrote %s rows to SQLite table %s", len(df), table_name)

            order_item_fact.to_sql(
                "order_item_sales",
                connection,
                if_exists="replace",
                index=False,
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_order_item_sales_order "
                "ON order_item_sales (order_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_order_item_sales_category "
                "ON order_item_sales (product_category_name)"
            )
    except Exception:
        logger.exception("Could not write SQLite database %s", path)
        raise
    finally:
        connection.close()

    logger.info("SQLite database written to %s", path)
    return path
