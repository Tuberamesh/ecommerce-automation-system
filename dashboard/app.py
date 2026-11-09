from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import streamlit as st

# Streamlit executes this file by path, which may put only dashboard/ on sys.path.
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dashboard.components import (
    apply_styles,
    render_app_header,
    render_global_filters,
    render_navigation,
)
from dashboard.config import PAGE_NAMES, PRODUCT_NAME
from dashboard.pages import (
    customers,
    order_explorer,
    overview,
    payments_operations,
    products,
    sales,
)


st.set_page_config(
    page_title=PRODUCT_NAME,
    layout="wide",
    initial_sidebar_state="auto",
)
apply_styles()
current_page = st.session_state.get("workspace-navigation", PAGE_NAMES[0])
if current_page not in PAGE_NAMES:
    current_page = PAGE_NAMES[0]
render_app_header(current_page)
selected_page = render_navigation(PAGE_NAMES)

try:
    active_filters = render_global_filters(selected_page)
except FileNotFoundError as error:
    st.error(f"{error}\n\nRun the existing pipeline first to create `database/ecommerce.db`.")
    st.stop()
except sqlite3.DatabaseError as error:
    st.error(f"Could not read the Olist database: {error}")
    st.stop()

pages = {
    "Executive Overview": overview.render,
    "Sales Analytics": sales.render,
    "Product Intelligence": products.render,
    "Customer Intelligence": customers.render,
    "Payments & Operations": payments_operations.render,
    "Order Explorer": order_explorer.render,
}

try:
    pages[selected_page](active_filters)
except FileNotFoundError as error:
    st.error(str(error))
except sqlite3.DatabaseError as error:
    st.error(f"Could not load this dashboard view: {error}")
