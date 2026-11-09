import pandas as pd
import streamlit as st

from dashboard.charts import bar_chart, donut_chart
from dashboard.components import (
    currency,
    format_table,
    full_width_kwargs,
    panel,
    percentage,
    render_empty,
    render_kpis,
    table_height,
)
from dashboard.queries import (
    DashboardFilters,
    delivery_performance,
    payment_installments,
    payment_reconciliation,
    payment_types,
    revenue_freight,
)


def render(filters: DashboardFilters) -> None:
    payment_mix = payment_types(filters)
    installment_data = payment_installments(filters)
    delivery = delivery_performance(filters)
    money = revenue_freight(filters).iloc[0]

    delivered_count = int(delivery["delivered_orders"].iloc[0]) if not delivery.empty else 0
    average_days = float(delivery["average_delivery_days"].iloc[0]) if delivered_count else 0.0
    delayed_pct = float(delivery["delayed_pct"].iloc[0]) if delivered_count else 0.0
    installments_mean = (
        float((installment_data["installments"] * installment_data["payment_records"]).sum()
              / installment_data["payment_records"].sum())
        if not installment_data.empty and installment_data["payment_records"].sum()
        else 0.0
    )
    render_kpis(
        [
            ("Delivered item freight", currency(money["delivered_freight"]), None, "Freight on delivered items."),
            ("Average delivery time", f"{average_days:.1f} days" if delivered_count else "—", None, "Purchase to customer delivery."),
            ("Delivered orders late", percentage(delayed_pct) if delivered_count else "—", None, "Past estimated delivery."),
            ("Mean payment installments", f"{installments_mean:.1f}" if not installment_data.empty else "—", None, "Weighted by payment records."),
        ]
    )

    left, right = st.columns(2)
    with left:
        with panel("Payment mix", "Payment values by type."):
            if not render_empty(payment_mix, "No payment records match the current filters."):
                payment_rank = payment_mix.sort_values("payment_value", ascending=False)
                bar_chart(
                    payment_rank,
                    "payment_value",
                    "payment_type",
                    {"payment_value": "Payment value (BRL)", "payment_type": "Payment type"},
                    horizontal=True,
                    key="payment-type-mix",
                )
    with right:
        with panel("Installment profile", "Payment records by installment count."):
            if not render_empty(installment_data, "No installment records match the current filters."):
                bar_chart(
                    installment_data,
                    "installments",
                    "payment_records",
                    {"installments": "Installments per payment record", "payment_records": "Payment records"},
                    key="payment-installments",
                )

    with panel("Delivery performance", "Elapsed time from purchase to customer delivery."):
        if not render_empty(delivery, "No delivered orders with complete delivery dates match these filters."):
            bar_chart(
                delivery,
                "delivery_bucket",
                "orders",
                {"delivery_bucket": "Purchase-to-delivery duration", "orders": "Delivered orders"},
                key="delivery-duration",
            )
            st.caption("Delay is the delivered-customer timestamp minus the estimated date; negative values are early.")

    with panel("Payment detail", "Counts and values by payment type."):
        if not render_empty(payment_mix, "No payment records match the current filters."):
            st.dataframe(
                format_table(
                    payment_mix,
                    {
                        "payment_type": "Payment type",
                        "payment_count": "Payment records",
                        "order_count": "Orders",
                        "payment_value": "Payment value",
                    },
                    integer_columns=("payment_count", "order_count"),
                    currency_columns=("payment_value",),
                ),
                hide_index=True,
                height=table_height(len(payment_mix)),
                **full_width_kwargs(st.dataframe),
            )

    with panel("Payment reconciliation", "Order-level payments compared with item price and freight totals."):
        reconciliation = payment_reconciliation(filters).iloc[0]
        reconciliation_table = pd.DataFrame(
            {
                "Measure": [
                    "Payment value",
                    "Item price",
                    "Freight",
                    "Item price + freight",
                    "Payment minus item price and freight",
                ],
                "Value (BRL)": [
                    reconciliation["payment_value"],
                    reconciliation["item_price"],
                    reconciliation["freight"],
                    reconciliation["item_price_plus_freight"],
                    reconciliation["difference"],
                ],
            }
        )
        st.dataframe(
            format_table(
                reconciliation_table,
                {"Measure": "Measure", "Value (BRL)": "Value (BRL)"},
                currency_columns=("Value (BRL)",),
            ),
            hide_index=True,
            height=table_height(len(reconciliation_table)),
            **full_width_kwargs(st.dataframe),
        )
        st.info(
            "Payment totals are aggregated from payment records; item price and freight are aggregated from order items. "
            "These are different financial measures, and a difference is not inherently an error. "
            "With a category filter, payments remain order-level while item totals include all items in qualifying orders."
        )
