import streamlit as st

from dashboard.charts import bar_chart, donut_chart
from dashboard.components import number, panel, percentage, render_empty, render_kpis
from dashboard.queries import (
    DashboardFilters,
    customer_distribution,
    customer_order_patterns,
    review_scores,
)


def render(filters: DashboardFilters) -> None:
    patterns = customer_order_patterns(filters)
    total_customers = int(patterns["customers"].sum()) if not patterns.empty else 0
    repeat_customers = (
        int(patterns.loc[patterns["order_count"] > 1, "customers"].sum())
        if not patterns.empty
        else 0
    )
    reviews = review_scores(filters)
    total_reviews = int(reviews["review_count"].sum()) if not reviews.empty else 0
    top_box = (
        int(reviews.loc[reviews["review_score"] >= 4, "review_count"].sum())
        if not reviews.empty
        else 0
    )
    average_score = (
        float((reviews["review_score"] * reviews["review_count"]).sum() / total_reviews)
        if total_reviews
        else 0.0
    )
    render_kpis(
        [
            ("Customers in selection", number(total_customers), None, "Distinct customer_unique_id values."),
            ("Customers with 2+ filtered orders", number(repeat_customers), None, "Within the active filters; not lifetime retention."),
            ("Average review score", f"{average_score:.2f}" if total_reviews else "—", None, "Recorded review rows, scored from 1 to 5."),
            ("Reviews scored 4–5", percentage(top_box / total_reviews * 100) if total_reviews else "—", None, "Share of review records, not a customer-level metric."),
        ]
    )

    left, right = st.columns(2)
    distribution = customer_distribution(filters)
    with left:
        with panel("Where customers order", "Top customer states ranked by distinct customers."):
            if not render_empty(distribution):
                top_states = distribution.nlargest(12, "customers").sort_values("customers")
                bar_chart(
                    top_states,
                    "customers",
                    "state",
                    {"customers": "Unique customers", "state": "Customer state"},
                    horizontal=True,
                    key="customer-state-distribution",
                )
    with right:
        with panel("Order frequency", "Distinct orders per customer within the active selection."):
            if not render_empty(patterns):
                bar_chart(
                    patterns,
                    "order_count",
                    "customers",
                    {"order_count": "Orders in selection", "customers": "Unique customers"},
                    key="customer-order-patterns",
                )

    with panel("Customer feedback", "Review counts by recorded score; repeated review IDs are retained."):
        if not render_empty(reviews):
            donut_chart(reviews, "review_score", "review_count", "customer-review-scores")
