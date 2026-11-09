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
from dashboard.queries import DashboardFilters, category_performance, product_performance


def render(filters: DashboardFilters) -> None:
    categories = category_performance(filters)
    if render_empty(categories, "No product items match the current filters."):
        return

    categories = categories.copy()
    revenue_total = categories["delivered_item_revenue"].sum()
    categories["revenue_contribution_pct"] = (
        categories["delivered_item_revenue"] / revenue_total * 100 if revenue_total else 0
    )
    render_kpis(
        [
            ("Delivered item revenue", currency(revenue_total), None, "Current category selection."),
            ("Categories represented", number(len(categories)), None, "Categories in the active filters."),
            ("Products represented", number(categories["products"].sum()), None, "Distinct product IDs by category."),
        ]
    )

    left, right = st.columns(2)
    with left:
        with panel("Category revenue ranking", "Top categories by delivered item revenue."):
            chart_data = categories.nlargest(12, "delivered_item_revenue").sort_values("delivered_item_revenue")
            bar_chart(
                chart_data,
                "delivered_item_revenue",
                "category",
                {"delivered_item_revenue": "Delivered item revenue (BRL)", "category": "Category"},
                horizontal=True,
                key="product-category-revenue",
            )
    with right:
        with panel("Products by category", "Top categories by distinct product IDs."):
            product_count_data = categories.nlargest(12, "products").sort_values("products")
            bar_chart(
                product_count_data,
                "products",
                "category",
                {"products": "Distinct products", "category": "Category"},
                horizontal=True,
                key="product-category-count",
            )

    category_leaders = categories.sort_values(
        "delivered_item_revenue", ascending=False
    ).head(10)
    with panel("Category leaders", "Highest delivered item revenue in the current selection."):
        st.dataframe(
            format_table(
                category_leaders[
                    ["category", "delivered_item_revenue", "revenue_contribution_pct", "delivered_orders", "products"]
                ],
                {
                    "category": "Category",
                    "delivered_item_revenue": "Item revenue",
                    "revenue_contribution_pct": "Revenue contribution",
                    "delivered_orders": "Delivered orders",
                    "products": "Products",
                },
                currency_columns=("delivered_item_revenue",),
                percentage_columns=("revenue_contribution_pct",),
                integer_columns=("delivered_orders", "products"),
            ),
            hide_index=True,
            height=table_height(len(category_leaders)),
            **full_width_kwargs(st.dataframe),
        )

    meaningful_bottom = categories[categories["delivered_item_revenue"] > 0].nsmallest(
        10, "delivered_item_revenue"
    )
    with panel("Emerging categories", "Lowest delivered revenue among categories with sales."):
        if meaningful_bottom.empty:
            st.caption("No categories have delivered revenue in this selection.")
        else:
            bottom_table = meaningful_bottom[
                ["category", "delivered_item_revenue", "revenue_contribution_pct", "delivered_orders"]
            ]
            st.dataframe(
                format_table(
                    bottom_table,
                    {
                        "category": "Category",
                        "delivered_item_revenue": "Item revenue",
                        "revenue_contribution_pct": "Revenue contribution",
                        "delivered_orders": "Delivered orders",
                    },
                    currency_columns=("delivered_item_revenue",),
                    percentage_columns=("revenue_contribution_pct",),
                    integer_columns=("delivered_orders",),
                ),
                hide_index=True,
                height=table_height(len(bottom_table)),
                **full_width_kwargs(st.dataframe),
            )

    with panel(
        "Product performance",
        "Product names are not present in the source; rows use Product ID. Category labels use English translations when available. Showing up to 50 products.",
    ):
        selected_category = st.selectbox(
            "Category",
            ["All categories", *categories["category"].fillna("Unknown").tolist()],
            key="product-category-drilldown",
        )
        category_value = None if selected_category == "All categories" else selected_category
        products = product_performance(filters, category=category_value, limit=50)
        st.caption(f"Showing {len(products):,} products in {selected_category}.")
        if render_empty(products, "No products match this category and filter combination."):
            return
        st.dataframe(
            format_table(
                products,
                {
                    "product_id": "Product ID",
                    "category": "Category",
                    "items_sold": "Items sold",
                    "orders": "Orders",
                    "delivered_item_revenue": "Delivered item revenue",
                    "delivered_freight": "Delivered freight",
                },
                integer_columns=("items_sold", "orders"),
                currency_columns=("delivered_item_revenue", "delivered_freight"),
            ),
            hide_index=True,
            height=table_height(len(products)),
            **full_width_kwargs(st.dataframe),
        )
