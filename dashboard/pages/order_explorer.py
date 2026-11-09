import pandas as pd
import streamlit as st

from dashboard.charts import bar_chart
from dashboard.components import (
    currency,
    format_table,
    full_width_kwargs,
    number,
    panel,
    render_empty,
    render_kpis,
    table_height,
)
from dashboard.queries import DashboardFilters, order_search_counts, search_orders


def render(filters: DashboardFilters) -> None:
    kpi_slot = st.empty()
    with panel(
        "Matching orders",
        "Search by full or partial order ID; results respect all global filters and are capped at 500.",
    ):
        search_term = st.text_input(
            "Search order ID",
            placeholder="Enter all or part of an order ID",
            key="order-explorer-search",
        )
        orders = search_orders(filters, search_term=search_term, limit=500)
        counts = order_search_counts(filters, search_term)
        if counts["matching_orders"] > 500:
            st.caption(
                f"Showing the first 500 of {counts['matching_orders']:,} matching orders. "
                "Narrow the search to see others."
            )
        else:
            label = "matching order" if counts["matching_orders"] == 1 else "matching orders"
            st.caption(f"{counts['matching_orders']:,} {label}.")
        with kpi_slot.container():
            render_kpis(
                [
                    ("Matching orders", number(counts["matching_orders"]), None, "All matches for the current search and filters."),
                    ("Delivered in matches", number(counts["delivered_orders"]), None, "Delivered orders across all matches."),
                    ("Customers in matches", number(counts["customers"]), None, "Distinct customers across all matches."),
                ]
            )
        if render_empty(orders, "No orders match the search and active filters."):
            return
        st.download_button(
            "Download displayed rows",
            data=orders.to_csv(index=False).encode("utf-8"),
            file_name="olist_filtered_orders.csv",
            mime="text/csv",
            key="download-filtered-orders",
        )
        display_orders = orders.replace("None", "—")
        st.dataframe(
            format_table(
                display_orders,
                {
                    "order_id": "Order ID",
                    "order_purchase_timestamp": "Purchase date",
                    "order_status": "Status",
                    "customer_unique_id": "Customer ID",
                    "customer_city": "Customer city",
                    "customer_state": "State",
                    "item_count": "Items",
                    "categories": "Categories",
                    "product_ids": "Product IDs",
                    "item_price": "Item price",
                    "freight": "Freight",
                    "item_total_value": "Item price + freight",
                    "payment_value": "Payment value",
                    "payment_types": "Payment types",
                    "max_installments": "Max installments",
                    "average_review_score": "Average review",
                    "review_count": "Review records",
                    "order_delivered_customer_date": "Delivered at",
                    "order_estimated_delivery_date": "Estimated delivery",
                    "delivery_days": "Delivery days",
                    "days_late": "Days late (+) / early (-)",
                },
                integer_columns=("item_count", "review_count"),
                currency_columns=("item_price", "freight", "item_total_value", "payment_value"),
                decimal_columns={
                    "average_review_score": 2,
                    "delivery_days": 1,
                    "days_late": 1,
                },
            ),
            hide_index=True,
            height=table_height(len(orders)),
            column_config={
                "Order ID": st.column_config.TextColumn("Order ID", width="medium"),
                "Customer ID": st.column_config.TextColumn("Customer ID", width="medium"),
                "Product IDs": st.column_config.TextColumn("Product IDs", width="large"),
            },
            **full_width_kwargs(st.dataframe),
        )

    status_counts = (
        orders["order_status"]
        .dropna()
        .value_counts()
        .rename_axis("order_status")
        .reset_index(name="orders")
    )
    state_counts = (
        orders.dropna(subset=["customer_state"])
        .groupby("customer_state", as_index=False)["order_id"]
        .nunique()
        .rename(columns={"customer_state": "state", "order_id": "orders"})
        .nlargest(12, "orders")
        .sort_values("orders")
    )

    with panel("Order detail", "Select an order from the filtered result set to inspect its context."):
        selected_id = st.selectbox("Order record", orders["order_id"].tolist(), key="selected-order")
        details = orders.loc[orders["order_id"] == selected_id].iloc[0]
        st.markdown(f"#### Order `{selected_id}`")
        a, b, c, d, e = st.columns(5)
        a.metric("Status", _display(details["order_status"], "Unknown"))
        b.metric("Customer state", _display(details["customer_state"], "Unknown"))
        c.metric("Freight", _money(details["freight"]))
        d.metric("Item price", _money(details["item_price"]))
        e.metric("Payment value", _money(details["payment_value"]))
        st.write(
            f"**Categories:** {_display(details['categories'], 'Unknown')}  \n"
            f"**Payment types:** {_display(details['payment_types'], 'Not recorded')}  \n"
            f"**Delivery:** {_display(details['delivery_days'], 'Not delivered')} days"
        )

    left, right = st.columns(2)
    with left:
        with panel("Order status mix", "Status counts among the displayed search results."):
            if not render_empty(status_counts):
                bar_chart(
                    status_counts,
                    "orders",
                    "order_status",
                    {"orders": "Orders", "order_status": "Order status"},
                    horizontal=True,
                    key="order-explorer-status-mix",
                )
    with right:
        with panel("Orders by customer state", "Top states among the displayed search results."):
            if not render_empty(state_counts):
                bar_chart(
                    state_counts,
                    "orders",
                    "state",
                    {"orders": "Orders", "state": "Customer state"},
                    horizontal=True,
                    key="order-explorer-state-orders",
                )

def _display(value: object, fallback: str) -> str:
    return fallback if pd.isna(value) else str(value)


def _money(value: object) -> str:
    return "—" if pd.isna(value) else currency(float(value), 2)
