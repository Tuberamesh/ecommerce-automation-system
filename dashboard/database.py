from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from dashboard.config import DATABASE_PATH


def connect_read_only(database_path: Path | str = DATABASE_PATH) -> sqlite3.Connection:
    """Open an existing SQLite database without permitting dashboard writes."""
    path = Path(database_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {path}")

    connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


@st.cache_data(ttl=300, show_spinner=False)
def read_query(
    sql: str,
    params: tuple[object, ...] = (),
    database_path: str = str(DATABASE_PATH),
) -> pd.DataFrame:
    """Run and briefly cache a parameterized read query."""
    connection = connect_read_only(database_path)
    try:
        return pd.read_sql_query(sql, connection, params=params)
    finally:
        connection.close()


def refresh_database_cache() -> None:
    read_query.clear()
