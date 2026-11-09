import streamlit as st

from dashboard.charts import bar_chart, line_chart
from dashboard.components import (
    currency,
    delta_text,
    format_table,
    full_width_kwargs,
    number,
    panel,
    render_empty,
    render_kpis,
    table_height,
)
from dashboard.queries import DashboardFilters, sales_by_state, sales_trend


def render(filters: DashboardFilters) -> None:
    grain_label = st.radio(
        "Time grain",
        ["Monthly", "Quarterly", "Yearly"],
        horizontal=True,
        index=2,
        key="sales-time-grain",
    )
    grain = {"Monthly": "month", "Quarterly": "quarter", "Yearly": "year"}[grain_label]
    trend = sales_trend(filters, grain)
    if render_empty(trend):
        return

    latest = trend.iloc[-1]
    previous = trend.iloc[-2] if len(trend) > 1 else None
    revenue_delta = delta_text(
        float(latest["delivered_item_revenue"]),
        float(previous["delivered_item_revenue"]) if previous is not None else 0,
    )
    order_delta = delta_text(
        float(latest["delivered_orders"]),
        float(previous["delivered_orders"]) if previous is not None else 0,
    )
    render_kpis(
        [
            (f"Latest {grain_label.lower()} delivered item revenue", currency(latest["delivered_item_revenue"]), revenue_delta, "Delivered item price."),
            (f"Latest {grain_label.lower()} delivered orders", number(latest["delivered_orders"]), order_delta, "Distinct delivered orders."),
            ("Latest all-status item value", currency(latest["all_status_item_value"]), None, "Includes every order status."),
        ]
    )
    st.caption("Compared with the preceding period shown; the latest period may be incomplete.")

    order_trend = trend.melt(
        id_vars="period",
        value_vars=["delivered_orders", "all_status_orders"],
        var_name="measure",
        value_name="orders",
    )
    left, right = st.columns(2)
    with left:
        with panel(f"{grain_label} value trends", "Delivered revenue excludes freight."):
            line_chart(
                trend,
                "period",
                ["delivered_item_revenue", "delivered_total_value", "all_status_item_value"],
                {
                    "period": "Purchase period",
                    "value": "Value (BRL)",
                    "delivered_item_revenue": "Delivered revenue",
                    "delivered_total_value": "Delivered total",
                    "all_status_item_value": "All-status value",
                },
                "sales-value-trend",
            )
    with right:
        with panel("Order volume", "Distinct orders by purchase period."):
            line_chart(
                order_trend,
                "period",
                "orders",
                {
                    "period": "Purchase period",
                    "orders": "Orders",
                    "measure": "Order status scope",
                    "delivered_orders": "Delivered orders",
                    "all_status_orders": "All-status orders",
                },
                "sales-order-trend",
                color="measure",
            )

    states = sales_by_state(filters)
    if render_empty(states):
        return
    left, right = st.columns(2)
    with left:
        with panel("Sales by customer state", "Top 12 states ranked by delivered item revenue."):
            state_order = (
                states.nlargest(12, "delivered_item_revenue")
                .sort_values("delivered_item_revenue")
            )
            bar_chart(
                state_order,
                "delivered_item_revenue",
                "state",
                {"state": "Customer state", "delivered_item_revenue": "Delivered item revenue (BRL)"},
                horizontal=True,
                key="sales-state-revenue",
            )
    with right:
        with panel("Order volume by state", "Delivered orders in the full state breakdown."):
            state_volume = states.nlargest(12, "delivered_orders").sort_values("delivered_orders")
            bar_chart(
                state_volume,
                "delivered_orders",
                "state",
                {"state": "Customer state", "delivered_orders": "Delivered orders"},
                horizontal=True,
                key="sales-state-order-volume",
            )
    with panel("Customer state detail", "Full state breakdown for the active filters."):
        state_table = states[
            [
                "state",
                "delivered_orders",
                "all_status_orders",
                "delivered_item_revenue",
                "delivered_freight",
                "all_status_item_value",
            ]
        ]
        st.dataframe(
            format_table(
                state_table,
                {
                    "state": "Customer state",
                    "delivered_orders": "Delivered orders",
                    "all_status_orders": "All-status orders",
                    "delivered_item_revenue": "Delivered item revenue",
                    "delivered_freight": "Delivered freight",
                    "all_status_item_value": "All-status item value",
                },
                integer_columns=("delivered_orders", "all_status_orders"),
                currency_columns=(
                    "delivered_item_revenue",
                    "delivered_freight",
                    "all_status_item_value",
                ),
            ),
            hide_index=True,
            height=table_height(len(state_table)),
            **full_width_kwargs(st.dataframe),
        )
