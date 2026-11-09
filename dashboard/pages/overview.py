import pandas as pd
import streamlit as st

from dashboard.charts import bar_chart, donut_chart, line_chart, show, status_mix_charts
from dashboard.components import (
    currency,
    escaped_currency,
    markdown_readout,
    number,
    render_empty,
    panel,
    render_kpis,
)
from dashboard.queries import (
    DashboardFilters,
    get_kpis,
    order_status_distribution,
    revenue_freight,
    sales_by_state,
    sales_trend,
)


def render(filters: DashboardFilters) -> None:
    kpis = get_kpis(filters)
    render_kpis(
        [
            ("Delivered item revenue", currency(kpis["delivered_revenue"]), None, "Item price; freight excluded."),
            ("Delivered orders", number(kpis["delivered_orders"]), None, "Orders marked delivered."),
            ("Unique customers", number(kpis["customers"]), None, "Distinct customers in this selection."),
            ("Average order value", currency(kpis["average_order_value"], 2), None, "Revenue per delivered item order."),
        ]
    )

    left, right = st.columns((1.55, 1))
    with left:
        with panel("Sales trajectory", "Delivered item revenue and all-status item value by purchase month."):
            trend = sales_trend(filters, "month")
            if not render_empty(trend):
                line_chart(
                    trend,
                    "period",
                    ["delivered_item_revenue", "all_status_item_value"],
                    {
                        "period": "Purchase month",
                        "value": "Value (BRL)",
                        "delivered_item_revenue": "Delivered item revenue",
                        "all_status_item_value": "All-status item value",
                    },
                    "overview-sales-trend",
                )
    with right:
        with panel(
            "Order status mix",
            "Logarithmic view keeps small status groups visible; the companion chart uses a linear scale.",
        ):
            statuses = order_status_distribution(filters)
            if not render_empty(statuses):
                all_statuses, non_delivered_statuses = status_mix_charts(statuses)
                log_tab, linear_tab = st.tabs(
                    ["All statuses (log scale)", "Non-delivered (linear)"]
                )
                with log_tab:
                    show(all_statuses, key="overview-order-status-log")
                with linear_tab:
                    if len(non_delivered_statuses.data[0].y):
                        show(
                            non_delivered_statuses,
                            key="overview-order-status-nondelivered",
                        )
                    else:
                        st.caption("No non-delivered orders in this selection.")

    left, right = st.columns((1.45, 1))
    with left:
        with panel("Regional demand", "Top customer states ranked by delivered item revenue."):
            states = sales_by_state(filters)
            if render_empty(states):
                top_states = pd.DataFrame()
            else:
                top_states = states.dropna(subset=["state"]).nlargest(10, "delivered_item_revenue")
                top_states = top_states.sort_values("delivered_item_revenue")
                bar_chart(
                    top_states,
                    "delivered_item_revenue",
                    "state",
                    {"delivered_item_revenue": "Delivered item revenue (BRL)", "state": "Customer state"},
                    horizontal=True,
                    key="overview-state-revenue",
                )
    with right:
        with panel("Delivered value composition", "Item price and freight are separate financial components."):
            money = revenue_freight(filters).iloc[0]
            comparison = pd.DataFrame(
                {
                    "Measure": ["Item price", "Freight"],
                    "Amount": [money["delivered_item_revenue"], money["delivered_freight"]],
                }
            )
            bar_chart(
                comparison,
                "Measure",
                "Amount",
                {"Amount": "Value (BRL)", "Measure": "Delivered amount"},
                color="Measure",
                key="overview-freight",
            )

    with panel("Executive readout", "Key context for this selection."):
        if kpis["delivered_orders"]:
            freight_share = (
                kpis["delivered_freight"]
                / (kpis["delivered_revenue"] + kpis["delivered_freight"])
                * 100
                if kpis["delivered_revenue"] + kpis["delivered_freight"]
                else 0
            )
            bullets = [
                f"Delivered item revenue is {escaped_currency(kpis['delivered_revenue'])}; freight is excluded.",
                f"Freight adds {escaped_currency(kpis['delivered_freight'])} ({freight_share:.1f}% of delivered item-plus-freight value).",
                "All-status item value includes non-delivered order statuses and is not revenue.",
            ]
            if not states.empty:
                best = states.dropna(subset=["state"]).nlargest(1, "delivered_item_revenue")
                if not best.empty:
                    from html import escape

                    bullets.insert(
                        2,
                        f"Highest delivered item revenue is in {escape(str(best.iloc[0]['state']))} "
                        f"({escaped_currency(best.iloc[0]['delivered_item_revenue'])}).",
                    )
            markdown_readout(bullets)
        else:
            st.info("There are no delivered orders in the current selection to summarize.")
