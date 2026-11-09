from __future__ import annotations

from math import log10

import plotly.express as px
import plotly.graph_objects as go
from plotly.basedatatypes import BaseTraceType
import streamlit as st

from dashboard.components import full_width_kwargs
from dashboard.config import COLORS

CHART_HEIGHT = 400
CHART_MARGIN = {"l": 24, "r": 20, "t": 48, "b": 44}


def theme(figure: go.Figure) -> go.Figure:
    figure.update_layout(
        height=CHART_HEIGHT,
        template="plotly_dark",
        margin=CHART_MARGIN,
        paper_bgcolor=COLORS["panel"],
        plot_bgcolor=COLORS["panel"],
        showlegend=False,
        font={
            "family": "Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, sans-serif",
            "color": COLORS["ink"],
            "size": 12,
        },
        colorway=COLORS["palette"],
        hoverlabel={
            "bgcolor": "#22262D",
            "bordercolor": COLORS["border"],
            "font": {"color": COLORS["ink"], "size": 12},
        },
    )
    figure.update_xaxes(
        showgrid=False,
        gridcolor=COLORS["grid"],
        linecolor=COLORS["border"],
        tickfont={"color": COLORS["muted"]},
        title_font={"color": COLORS["ink"]},
        automargin=True,
    )
    figure.update_yaxes(
        showgrid=True,
        gridcolor=COLORS["grid"],
        zeroline=False,
        linecolor=COLORS["border"],
        tickfont={"color": COLORS["muted"]},
        title_font={"color": COLORS["ink"]},
        automargin=True,
    )
    return figure


def _series_label(trace: BaseTraceType, labels: dict[str, str], index: int) -> str:
    if trace.name and trace.name in labels:
        return labels[trace.name]
    if trace.name and trace.name in labels.values():
        return trace.name
    if trace.name:
        return " ".join(part.capitalize() for part in trace.name.replace("_", " ").split())
    return f"Series {index + 1}"


def show(
    figure: go.Figure,
    key: str | None = None,
    *,
    labels: dict[str, str] | None = None,
    show_legend: bool = False,
) -> None:
    if len(figure.data) > 1:
        if key is None:
            raise ValueError("Multi-series charts require a stable key for their series switches.")
        series_labels = labels or {}
        for start in range(0, len(figure.data), 4):
            traces = figure.data[start : start + 4]
            columns = st.columns(len(traces))
            for column, (index, trace) in zip(
                columns,
                enumerate(traces, start=start),
                strict=True,
            ):
                label = _series_label(trace, series_labels, index)
                with column:
                    trace.visible = st.toggle(
                        label,
                        value=True,
                        key=f"{key}-series-{index}",
                        help=f"Show or hide {label} in this chart.",
                    )
        show_legend = False

    render_plotly_chart(figure, key, show_legend=show_legend)


def render_plotly_chart(
    figure: go.Figure,
    key: str | None = None,
    *,
    show_legend: bool = False,
) -> None:
    styled_figure = theme(figure)
    styled_figure.update_layout(dragmode=False)
    styled_figure.update_xaxes(fixedrange=True)
    styled_figure.update_yaxes(fixedrange=True)
    if show_legend:
        styled_figure.update_layout(
            showlegend=True,
            legend={
                "orientation": "h",
                "x": 0.5,
                "xanchor": "center",
                "y": 1.08,
                "yanchor": "bottom",
                "font": {"color": COLORS["muted"], "size": 11},
                "title_text": "",
            },
        )
    st.plotly_chart(
        styled_figure,
        key=key,
        **full_width_kwargs(st.plotly_chart),
        config={
            "displayModeBar": False,
            "scrollZoom": False,
            "doubleClick": False,
            "responsive": True,
        },
    )


def status_mix_charts(data) -> tuple[go.Figure, go.Figure]:
    total_orders = int(data["order_count"].sum())
    ordered = data.sort_values("order_count", ascending=True)
    status_names = [str(status).replace("_", " ").capitalize() for status in ordered["order_status"]]
    counts = [int(value) for value in ordered["order_count"]]
    shares = [count / total_orders * 100 if total_orders else 0 for count in counts]
    colors = [
        COLORS["primary"] if str(status).lower() == "delivered" else COLORS["secondary"]
        for status in ordered["order_status"]
    ]

    log_figure = go.Figure(
        go.Bar(
            x=counts,
            y=status_names,
            base=0.5,
            orientation="h",
            marker_color=colors,
            customdata=shares,
            hovertemplate=(
                "%{y}<br>Orders: %{x:,.0f}<br>Share: %{customdata:.1f}%<extra></extra>"
            ),
        )
    )
    max_count = max(counts, default=1)
    log_figure.update_layout(
        showlegend=False,
    )
    log_figure.update_xaxes(
        type="log",
        range=[log10(0.5), log10(max_count * 5)],
        title_text="Orders (log scale)",
        tickvals=[value for value in (1, 10, 100, 1_000, 10_000, 100_000, 1_000_000) if value <= max_count * 5],
        ticktext=[
            f"{value:,}"
            for value in (1, 10, 100, 1_000, 10_000, 100_000, 1_000_000)
            if value <= max_count * 5
        ],
    )
    log_figure.update_yaxes(
        categoryorder="array",
        categoryarray=status_names,
        title_text=None,
    )

    non_delivered = ordered[ordered["order_status"].str.lower() != "delivered"]
    linear_names = [
        str(status).replace("_", " ").capitalize()
        for status in non_delivered["order_status"]
    ]
    linear_counts = [int(value) for value in non_delivered["order_count"]]
    linear_shares = [
        count / total_orders * 100 if total_orders else 0 for count in linear_counts
    ]
    linear_figure = go.Figure(
        go.Bar(
            x=linear_counts,
            y=linear_names,
            orientation="h",
            marker_color=COLORS["secondary"],
            customdata=linear_shares,
            hovertemplate=(
                "%{y}<br>Orders: %{x:,.0f}<br>Share of all orders: %{customdata:.1f}%<extra></extra>"
            ),
        )
    )
    linear_figure.update_layout(
        showlegend=False,
    )
    linear_figure.update_xaxes(title_text="Non-delivered orders", tickformat=",.0f")
    linear_figure.update_yaxes(
        categoryorder="array",
        categoryarray=linear_names,
        title_text=None,
    )
    return log_figure, linear_figure


def line_chart(
    data,
    x: str,
    y: str | list[str],
    labels: dict[str, str],
    key: str | None = None,
    color: str | None = None,
):
    figure = px.line(
        data,
        x=x,
        y=y,
        color=color,
        labels=labels,
        color_discrete_sequence=COLORS["palette"],
        markers=True,
    )
    figure.update_traces(line={"width": 2.8}, marker={"size": 6}, selector=dict(type="scatter"))
    for trace in figure.data:
        trace.name = labels.get(trace.name, trace.name)
    figure.update_layout(legend_title_text="")
    fields = [y] if isinstance(y, str) else y
    money_axis = False
    for field in fields:
        label = labels.get(field, "").lower()
        if any(token in label for token in ("amount", "revenue", "value", "freight", "price")):
            figure.update_yaxes(tickprefix="R$ ", tickformat=",.0f")
            money_axis = True
    hover_value = "R$ %{y:,.2f}" if money_axis else "%{y:,.0f}"
    figure.update_traces(
        hovertemplate=f"%{{x}}<br>%{{fullData.name}}: {hover_value}<extra></extra>"
    )
    show(figure, key, labels=labels)


def bar_chart(
    data,
    x: str,
    y: str,
    labels: dict[str, str],
    *,
    horizontal: bool = False,
    color: str | None = None,
    key: str | None = None,
):
    if horizontal:
        figure = px.bar(
            data,
            x=x,
            y=y,
            labels=labels,
            color=color,
            orientation="h",
            color_discrete_sequence=COLORS["palette"],
        )
    else:
        figure = px.bar(
            data,
            x=x,
            y=y,
            labels=labels,
            color=color,
            color_discrete_sequence=COLORS["palette"],
        )
    figure.update_layout(legend_title_text="")
    money_x = any(token in labels.get(x, "").lower() for token in ("amount", "revenue", "value", "freight", "price"))
    money_y = any(token in labels.get(y, "").lower() for token in ("amount", "revenue", "value", "freight", "price"))
    if money_x:
        figure.update_xaxes(tickprefix="R$ ", tickformat=",.0f")
    if money_y:
        figure.update_yaxes(tickprefix="R$ ", tickformat=",.0f")
    figure.update_traces(marker_line_width=0)
    if horizontal:
        hover_value = "R$ %{x:,.2f}" if money_x else "%{x:,.0f}"
        hover_category = "%{y}"
    else:
        hover_value = "R$ %{y:,.2f}" if money_y else "%{y:,.0f}"
        hover_category = "%{x}"
    figure.update_traces(
        hovertemplate=f"{hover_category}<br>{hover_value}<extra></extra>"
    )
    show(figure, key, labels=labels)


def donut_chart(data, names: str, values: str, key: str | None = None):
    figure = px.pie(
        data,
        names=names,
        values=values,
        hole=0.58,
        color_discrete_sequence=COLORS["palette"],
    )
    figure.update_layout(legend_title_text="")
    is_money = any(token in values.lower() for token in ("amount", "revenue", "value", "freight", "price"))
    hover_value = "R$ %{value:,.2f}" if is_money else "%{value:,.0f}"
    figure.update_traces(
        textinfo="none",
        marker={"line": {"color": COLORS["panel"], "width": 2}},
        hovertemplate=f"%{{label}}<br>{hover_value}<br>Share: %{{percent}}<extra></extra>",
    )
    show(figure, key, show_legend=True)
