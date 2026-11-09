from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from html import escape
from inspect import signature
from textwrap import dedent
from typing import Any, Callable, Generator, Sequence

import pandas as pd
import streamlit as st
from pandas.io.formats.style import Styler

from dashboard.config import (
    COLORS,
    PAGE_COPY,
    PAGE_EYEBROWS,
    PRODUCT_NAME,
    PRODUCT_SUBTITLE,
)
from dashboard.queries import DashboardFilters, get_filter_options


def apply_styles() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;650;700&display=swap');
        :root {{
            color-scheme: dark;
            --oci-bg: #0F1115;
            --oci-sidebar: #181B21;
            --oci-panel: #181B21;
            --oci-border: #262A32;
            --oci-text: {COLORS["ink"]};
            --oci-muted: {COLORS["muted"]};
            --oci-green: {COLORS["primary"]};
            --oci-amber: {COLORS["accent"]};
        }}
        html, body, .stApp, [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {{
            background: var(--oci-bg);
            color: var(--oci-text);
            font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }}
        section.main > div.block-container,
        [data-testid="stMainBlockContainer"],
        .block-container {{
            max-width: 100% !important;
            padding: 1rem 1.5rem 1.5rem !important;
            box-sizing: border-box;
        }}
        .stApp:has(.oci-sidebar-brand) [data-testid="stMainBlockContainer"] {{
            padding-top: 2rem !important;
        }}
        [data-testid="stMain"] {{
            min-width: 0;
        }}
        [data-testid="stMainBlockContainer"] [data-testid="stHorizontalBlock"],
        [data-testid="stMainBlockContainer"] [data-testid="stColumn"],
        [data-testid="stMainBlockContainer"] [data-testid="stPlotlyChart"],
        [data-testid="stMainBlockContainer"] [data-testid="stDataFrame"] {{
            min-width: 0;
            max-width: 100%;
            box-sizing: border-box;
        }}
        section.main [data-testid="stDataFrame"],
        section.main [data-testid="stDataFrameResizable"] {{
            width: 100% !important;
            max-width: 100%;
            box-sizing: border-box;
        }}
        [data-testid="stHeader"] {{
            background: transparent !important;
        }}
        [data-testid="stToolbar"] {{
            color: var(--oci-muted);
        }}

        [data-testid="stSidebar"] {{
            box-sizing: border-box;
            overflow-x: hidden;
            background: var(--oci-sidebar) !important;
            border-right: 1px solid #303030;
        }}
        [data-testid="stSidebarHeader"] {{
            height: 44px !important;
            min-height: 44px !important;
            padding: 0 1rem !important;
        }}
        @media (min-width: 761px) {{
            [data-testid="stSidebar"][aria-expanded="true"] {{
                box-sizing: border-box;
                width: 290px !important;
                min-width: 290px !important;
                max-width: 290px !important;
            }}
        }}
        [data-testid="stSidebar"] > div:first-child,
        [data-testid="stSidebar"] [data-testid="stSidebarContent"],
        [data-testid="stSidebar"] [data-testid="stSidebarUserContent"],
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"],
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {{
            background: var(--oci-sidebar) !important;
            border-color: transparent !important;
            border-radius: 0 !important;
            box-shadow: none !important;
        }}
        [data-testid="stSidebarContent"] {{
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            height: calc(100vh - 44px);
            min-width: 0;
            overflow-x: hidden;
            padding: 0 1rem .75rem !important;
        }}
        [data-testid="stSidebar"] [data-testid="stSidebarUserContent"],
        [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div,
        [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlockBorderWrapper"] > div,
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"],
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stSidebar"] [data-testid="element-container"],
        [data-testid="stSidebar"] [data-testid="stRadio"],
        [data-testid="stSidebar"] [data-testid="stRadio"] > div,
        [data-testid="stSidebar"] [data-testid="stRadio"] label,
        [data-testid="stSidebar"] [data-testid="stMultiSelect"],
        [data-testid="stSidebar"] [data-testid="stButton"],
        [data-testid="stSidebar"] [data-testid="stButton"] button,
        [data-testid="stSidebar"] [data-baseweb="select"],
        .oci-sidebar-brand,
        .oci-sidebar-brand .oci-app-title,
        .oci-sidebar-brand .oci-app-subtitle {{
            box-sizing: border-box;
            width: 100%;
            max-width: 100%;
            min-width: 0;
        }}
        [data-testid="stSidebarUserContent"] {{
            position: relative;
            display: flex;
            flex: 1 1 auto;
            min-height: 0;
            padding-left: 0 !important;
            padding-right: 0 !important;
            padding-top: 0 !important;
            padding-bottom: .5rem !important;
        }}
        [data-testid="stSidebarUserContent"] > div {{
            display: flex;
            flex: 1 1 auto;
            height: 100%;
            flex-direction: column;
            min-height: 0;
        }}
        [data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlockBorderWrapper"] {{
            display: flex;
            flex: 1 1 auto;
            min-height: 0;
        }}
        [data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] {{
            display: flex;
            flex: 1 1 auto;
            flex-direction: column;
            min-height: 100%;
            gap: .35rem;
        }}
        [data-testid="stSidebarUserContent"] [data-testid="element-container"]:has(.oci-sidebar-actions) {{
            margin-top: auto !important;
        }}
        [data-testid="stSidebarUserContent"] [data-testid="element-container"]:has(.oci-nav-label) {{
            width: 100%;
        }}
        [data-testid="stSidebar"] *,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label {{
            color: var(--oci-text);
        }}
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {{
            color: var(--oci-muted) !important;
        }}
        [data-testid="stSidebarNav"] {{
            display: none !important;
        }}
        [data-testid="stSidebar"] hr {{
            border-color: var(--oci-border);
            margin: .55rem 0;
        }}
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarCollapseButton"] *,
        button[aria-label="Collapse sidebar"],
        button[aria-label="Collapse sidebar"] *,
        button[aria-label="Expand sidebar"],
        button[aria-label="Expand sidebar"] * {{
            visibility: visible !important;
        }}
        [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"],
        button[aria-label="Expand sidebar"] [data-testid="stIconMaterial"] {{
            color: var(--oci-muted) !important;
        }}

        .oci-side-label {{
            color: var(--oci-muted);
            font-size: .68rem;
            font-weight: 700;
            letter-spacing: .09em;
            margin: 0 0 .3rem;
            text-transform: uppercase;
        }}
        .oci-nav-label {{
            font-size: .9rem;
            letter-spacing: .12em;
            margin: 1.2rem 0 .75rem;
        }}
        .oci-sidebar-brand {{
            margin: .15rem 0 .3rem;
            padding: 0;
            text-align: left;
        }}
        .oci-sidebar-brand .oci-app-title {{
            font-size: 1.25rem;
            line-height: 1.2;
            overflow-wrap: anywhere;
            white-space: normal;
        }}
        .oci-sidebar-brand .oci-app-subtitle {{
            font-size: .75rem;
            line-height: 1.3;
            margin-top: .2rem;
            overflow-wrap: anywhere;
            white-space: normal;
        }}
        .oci-filter-label {{
            margin-top: .1rem;
            margin-bottom: .55rem;
        }}
        [data-testid="stSidebar"] [data-testid="stRadio"] > label {{
            display: none !important;
        }}
        [data-testid="stSidebar"] [data-testid="stRadio"] > div {{
            gap: .12rem;
        }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label {{
            position: relative;
            display: flex;
            align-items: center;
            min-height: 44px;
            padding: .35rem .6rem;
            margin: 0;
            border: 1px solid transparent;
            border-radius: 4px;
        }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child {{
            display: none !important;
        }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label p {{
            color: #C4C4C4 !important;
            font-size: .95rem;
            line-height: 1.2;
            margin: 0;
            overflow-wrap: anywhere;
            white-space: normal;
        }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{
            background: #22262D;
            border-color: var(--oci-border);
            border-left: 3px solid var(--oci-green);
            padding-left: calc(.6rem - 2px);
        }}
        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {{
            color: #FFFFFF !important;
            font-weight: 650;
        }}

        .oci-app-header {{
            margin: 0 0 1.15rem;
            padding: .1rem 0 0;
            text-align: center;
        }}
        .oci-app-title {{
            color: var(--oci-text);
            font-size: 2.8rem;
            font-weight: 800;
            letter-spacing: -.04em;
            line-height: 1.12;
        }}
        .oci-app-subtitle {{
            color: var(--oci-muted);
            font-size: 1.4rem;
            font-weight: 400;
            line-height: 1.3;
            margin-top: .15rem;
        }}
        .oci-page-heading {{
            margin: 0;
            padding: 0;
        }}
        .oci-page-title {{
            color: var(--oci-text);
            font-size: 2.1rem;
            font-weight: 700;
            letter-spacing: -.025em;
            line-height: 1.05;
            margin: 0;
        }}
        .oci-page-accent {{
            width: 48px;
            height: 3px;
            margin: .4rem 0 .35rem;
            background: var(--oci-green);
        }}
        .oci-page-description {{
            color: var(--oci-muted);
            font-size: 1rem;
            line-height: 1.4;
            margin: .15rem 0 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .oci-header-rule {{
            border-bottom: 1px solid var(--oci-border);
            margin: .9rem 0 1.15rem;
        }}
        section.main [data-testid="stCaptionContainer"] {{
            margin-top: 0;
            margin-bottom: .15rem;
        }}
        h1, h2, h3, h4 {{
            color: var(--oci-text);
            letter-spacing: -.015em;
        }}
        .stMarkdown p {{
            line-height: 1.5;
        }}
        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] * {{
            color: var(--oci-muted) !important;
        }}
        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] label {{
            color: var(--oci-muted) !important;
            font-size: .75rem;
            font-weight: 550;
        }}
        .oci-eyebrow {{
            color: var(--oci-muted);
            font-size: .62rem;
            font-weight: 650;
            letter-spacing: .09em;
            line-height: 1.2;
            margin: 0 0 .12rem;
            text-transform: uppercase;
        }}
        .oci-panel-heading {{
            margin: 0 0 .25rem;
        }}
        .oci-panel-title {{
            color: var(--oci-text);
            font-size: 1.1rem;
            font-weight: 700;
            letter-spacing: -.01em;
            line-height: 1.25;
        }}
        .oci-kpi {{
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            min-height: 116px;
            height: 100%;
            box-sizing: border-box;
            padding: .8rem .85rem .7rem;
            background: var(--oci-panel);
            border: 1px solid var(--oci-border);
            border-left: 3px solid var(--oci-amber);
            border-radius: 4px;
        }}
        .oci-kpi--revenue {{
            border-left-color: var(--oci-green);
        }}
        .oci-kpi-label {{
            min-height: 1.8rem;
            color: var(--oci-muted);
            font-size: .63rem;
            font-weight: 650;
            letter-spacing: .075em;
            line-height: 1.35;
            text-transform: uppercase;
        }}
        .oci-kpi-value {{
            color: var(--oci-text);
            font-size: clamp(1.3rem, 1.8vw, 1.7rem);
            font-weight: 700;
            font-variant-numeric: tabular-nums;
            letter-spacing: -.025em;
            line-height: 1.2;
            margin-top: .3rem;
            white-space: nowrap;
        }}
        .oci-kpi-detail {{
            color: var(--oci-muted);
            font-size: .69rem;
            line-height: 1.35;
            margin-top: auto;
            padding-top: .3rem;
            min-height: .95rem;
        }}
        .oci-kpi-detail:empty {{
            display: none;
        }}
        section.main [data-testid="stVerticalBlockBorderWrapper"] {{
            background: transparent !important;
            border: 0 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
        }}
        section.main [data-testid="stVerticalBlockBorderWrapper"]:has(
            > div > [data-testid="stVerticalBlock"] >
            [data-testid="element-container"] .oci-panel-heading
        ) {{
            background: var(--oci-panel) !important;
            border: 1px solid var(--oci-border) !important;
            border-radius: 4px !important;
        }}
        section.main [data-testid="stVerticalBlockBorderWrapper"]:has(
            > div > [data-testid="stVerticalBlock"] >
            [data-testid="element-container"] .oci-panel-heading
        ) > div {{
            border-radius: inherit;
        }}
        [data-testid="stAlert"] {{
            background: #302817;
            border: 1px solid #5E4923;
            color: #F0D8A5;
        }}

        input, textarea, [data-baseweb="input"] input,
        [data-testid="stDateInput"] input {{
            background: #181B21 !important;
            color: var(--oci-text) !important;
            border-color: var(--oci-border) !important;
            caret-color: var(--oci-green);
        }}
        input::placeholder, textarea::placeholder {{
            color: #858585 !important;
            opacity: 1;
        }}
        [data-baseweb="select"] > div {{
            background: #181B21 !important;
            color: var(--oci-text) !important;
            border-color: var(--oci-border) !important;
        }}
        [data-baseweb="select"] input, [data-baseweb="select"] span,
        [data-baseweb="select"] [data-testid="stMarkdownContainer"] {{
            color: var(--oci-text) !important;
        }}
        [data-baseweb="tag"] {{
            background: #35432B !important;
            border: 1px solid #536D3E !important;
        }}
        [data-baseweb="tag"] span {{
            color: #E2F2D2 !important;
        }}
        [data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"],
        [role="dialog"], [data-baseweb="calendar"] {{
            background: #181B21 !important;
            color: var(--oci-text) !important;
            border-color: var(--oci-border) !important;
        }}
        [role="option"], [role="listbox"] *, [data-baseweb="calendar"] *,
        [role="dialog"] * {{
            color: var(--oci-text);
        }}
        [role="option"]:hover, [role="option"][aria-selected="true"],
        [data-baseweb="calendar"] button:hover {{
            background: #22262D !important;
        }}
        [data-baseweb="calendar"] button[aria-pressed="true"] {{
            background: var(--oci-green) !important;
            color: #111111 !important;
        }}
        [data-baseweb="calendar"] [role="gridcell"][aria-label*="Selected"] {{
            background: #273A2B !important;
            color: #E2F2D2 !important;
            border-radius: 5px;
            font-weight: 700;
        }}
        [data-testid="stButton"] button,
        [data-testid="stDownloadButton"] button {{
            color: var(--oci-text);
            background: #22262D;
            border: 1px solid var(--oci-border);
            border-radius: 4px;
            font-weight: 550;
            min-height: 1.9rem;
        }}
        [data-testid="stSidebar"] [data-testid="stButton"] button {{
            min-width: 0;
            white-space: nowrap;
            text-align: center;
        }}
        [data-testid="stSidebar"] [data-testid="stButton"] button p {{
            width: 100%;
            white-space: nowrap;
            text-align: center;
        }}
        [data-testid="stSidebar"] [data-testid="stButton"] button > div {{
            white-space: nowrap;
        }}
        [data-testid="stButton"] button:hover,
        [data-testid="stDownloadButton"] button:hover {{
            color: #FFFFFF;
            background: #292E36;
            border-color: #3A404A;
        }}
        [data-testid="stButton"] button[kind="primary"] {{
            color: #171717;
            background: var(--oci-amber);
            border-color: var(--oci-amber);
        }}
        [data-testid="stDataFrame"], [data-testid="stTable"] {{
            border: 1px solid var(--oci-border);
            border-radius: 4px;
            background: var(--oci-panel);
        }}
        [data-testid="stDataFrame"] iframe {{
            color-scheme: dark;
        }}
        [data-testid="stExpander"] {{
            border-color: var(--oci-border);
            background: var(--oci-panel);
            border-radius: 4px;
        }}
        [data-testid="stElementToolbar"] button[aria-label*="fullscreen" i],
        [data-testid="stElementToolbar"] button[title*="fullscreen" i] {{
            display: none !important;
        }}
        .oci-readout {{
            max-width: 900px;
            color: var(--oci-text);
            line-height: 1.6;
            overflow-wrap: anywhere;
            white-space: normal;
        }}
        .oci-readout ul {{
            margin: .2rem 0 0;
            padding-left: 1.25rem;
        }}
        .oci-readout li {{
            margin: .22rem 0;
            line-height: 1.6;
        }}
        a {{
            color: #A7D47A;
        }}
        ::selection {{
            color: #111111;
            background: #B4D995;
        }}
        @media (max-width: 760px) {{
            section.main > div.block-container,
            [data-testid="stMainBlockContainer"],
            .block-container {{
                padding: 1rem 1rem 1.25rem !important;
            }}
            .oci-kpi-value {{
                font-size: 1.25rem;
            }}
            .oci-page-title {{
                font-size: 1.8rem;
            }}
            .oci-app-title {{
                font-size: 2rem;
            }}
            .oci-app-subtitle {{
                font-size: 1rem;
            }}
            .oci-page-description {{
                font-size: .9rem;
            }}
            .oci-kpi {{
                min-height: 104px;
                padding: .65rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_app_header(active_page: str) -> None:
    app_header = dedent(f"""
        <div class="oci-app-header">
            <div class="oci-app-title">{escape(PRODUCT_NAME)}</div>
            <div class="oci-app-subtitle">{escape(PRODUCT_SUBTITLE)}</div>
        </div>
        """)
    if active_page == "Executive Overview":
        st.markdown(app_header, unsafe_allow_html=True)
        return

    st.sidebar.markdown(
        dedent(f"""
        <div class="oci-sidebar-brand">
            <div class="oci-app-title">{escape(PRODUCT_NAME)}</div>
            <div class="oci-app-subtitle">{escape(PRODUCT_SUBTITLE)}</div>
        </div>
        """),
        unsafe_allow_html=True,
    )
    st.sidebar.divider()


def render_navigation(page_names: Sequence[str]) -> str:
    st.sidebar.markdown(
        '<div class="oci-side-label oci-nav-label">Navigation</div>',
        unsafe_allow_html=True,
    )
    icons = {
        "Executive Overview": "space_dashboard",
        "Sales Analytics": "query_stats",
        "Product Intelligence": "inventory_2",
        "Customer Intelligence": "group",
        "Payments & Operations": "local_shipping",
        "Order Explorer": "receipt_long",
    }
    return st.sidebar.radio(
        "Navigation",
        page_names,
        format_func=lambda page: f":material/{icons.get(page, 'dashboard')}: {page}",
        label_visibility="collapsed",
        key="workspace-navigation",
    )


def render_page_header(title: str, description: str, eyebrow: str) -> None:
    st.markdown(
        dedent(f"""
        <div class="oci-page-heading">
            <div class="oci-eyebrow">{escape(eyebrow)}</div>
            <h1 class="oci-page-title">{escape(title)}</h1>
            <div class="oci-page-accent"></div>
            <p class="oci-page-description">{escape(description)}</p>
        </div>
        """),
        unsafe_allow_html=True,
    )


def full_width_kwargs(command: Callable[..., Any]) -> dict[str, Any]:
    width_parameter = signature(command).parameters.get("width")
    if width_parameter and (
        width_parameter.default == "stretch"
        or "stretch" in str(width_parameter.annotation)
    ):
        return {"width": "stretch"}
    return {"use_container_width": True}


@contextmanager
def panel(title: str, description: str | None = None) -> Generator[None, None, None]:
    with st.container(border=True):
        st.markdown(
            dedent(f"""
            <div class="oci-panel-heading">
                <div class="oci-panel-title">{escape(title)}</div>
            </div>
            """),
            unsafe_allow_html=True,
        )
        if description:
            st.caption(description)
        yield


def render_kpis(metrics: Sequence[tuple[str, ...]]) -> None:
    columns = st.columns(len(metrics))
    for column, metric in zip(columns, metrics, strict=True):
        label, value = metric[:2]
        delta = metric[2] if len(metric) > 3 else None
        context = metric[3] if len(metric) > 3 else metric[2] if len(metric) > 2 else None
        accent = "revenue" if "revenue" in label.lower() else "support"
        detail = " · ".join(str(part) for part in (delta, context) if part)
        with column:
            st.markdown(
                f"""
                <div class="oci-kpi oci-kpi--{accent}">
                    <div class="oci-kpi-label">{escape(label)}</div>
                    <div class="oci-kpi-value">{escape(str(value))}</div>
                    <div class="oci-kpi-detail">{escape(detail)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_empty(
    data: pd.DataFrame,
    message: str = "No records match the current filters.",
) -> bool:
    if data.empty:
        st.info(message)
        return True
    return False


def table_height(row_count: int, max_height: int = 420) -> int:
    return min(max_height, max(120, 42 + row_count * 34))


def format_table(
    data: pd.DataFrame,
    column_labels: dict[str, str],
    *,
    currency_columns: Sequence[str] = (),
    integer_columns: Sequence[str] = (),
    percentage_columns: Sequence[str] = (),
    decimal_columns: dict[str, int] | None = None,
) -> Styler:
    display_data = data.rename(columns=column_labels)
    formatters: dict[str, Callable[[object], str]] = {}

    for column in currency_columns:
        formatters[column_labels.get(column, column)] = _currency_cell
    for column in integer_columns:
        formatters[column_labels.get(column, column)] = _integer_cell
    for column in percentage_columns:
        formatters[column_labels.get(column, column)] = _percentage_cell
    for column, decimals in (decimal_columns or {}).items():
        formatters[column_labels.get(column, column)] = (
            lambda value, places=decimals: _decimal_cell(value, places)
        )

    return display_data.style.format(formatters, na_rep="—")


def _currency_cell(value: object) -> str:
    return "—" if pd.isna(value) else currency(float(value), 2)


def _integer_cell(value: object) -> str:
    return "—" if pd.isna(value) else f"{float(value):,.0f}"


def _percentage_cell(value: object) -> str:
    return "—" if pd.isna(value) else f"{float(value):.1f}%"


def _decimal_cell(value: object, decimals: int) -> str:
    return "—" if pd.isna(value) else f"{float(value):,.{decimals}f}"


def markdown_readout(bullets: Sequence[str]) -> None:
    items = "".join(f"<li>{bullet}</li>" for bullet in bullets)
    st.markdown(
        f'<div class="oci-readout"><ul>{items}</ul></div>',
        unsafe_allow_html=True,
    )


def escaped_currency(value: float | int, decimals: int = 0) -> str:
    return escape(currency(value, decimals)).replace("$", "&#36;")


def render_global_filters(
    active_page: str,
    database_path: str | None = None,
) -> DashboardFilters:
    options = get_filter_options(database_path)
    title, description = PAGE_COPY[active_page]
    date_key = "global_date_range"
    min_date = _as_date(options["min_date"])
    max_date = _as_date(options["max_date"])
    default_date_range = (min_date, max_date) if min_date and max_date else ()
    if date_key not in st.session_state:
        st.session_state[date_key] = default_date_range
    title_column, date_column = st.columns(
        (2.3, 1),
        vertical_alignment="bottom",
    )
    with title_column:
        render_page_header(title, description, PAGE_EYEBROWS[active_page])
    with date_column:
        date_value = st.date_input(
            "Purchase date",
            min_value=min_date,
            max_value=max_date,
            key=date_key,
        )
    st.markdown(
        '<div class="oci-header-rule"></div>',
        unsafe_allow_html=True,
    )

    if isinstance(date_value, tuple):
        start_date = date_value[0].isoformat() if len(date_value) > 0 and date_value[0] else None
        end_date = date_value[1].isoformat() if len(date_value) > 1 and date_value[1] else None
    else:
        start_date = end_date = None

    st.sidebar.divider()
    st.sidebar.markdown(
        '<div class="oci-side-label oci-filter-label">Filters</div>',
        unsafe_allow_html=True,
    )
    states = st.sidebar.multiselect("Customer state", options["states"], key="global_states")
    categories = st.sidebar.multiselect(
        "Product category",
        options["categories"],
        key="global_categories",
    )
    statuses = st.sidebar.multiselect(
        "Order status",
        options["statuses"],
        key="global_statuses",
    )

    date_filter_active = bool(start_date and end_date) and (
        start_date != options["min_date"] or end_date != options["max_date"]
    )
    active_count = int(date_filter_active) + len(states) + len(categories) + len(statuses)
    st.sidebar.caption(
        f"{active_count} active filter{'s' if active_count != 1 else ''}"
    )
    with st.sidebar.container():
        st.markdown(
            '<div class="oci-sidebar-actions"></div>',
            unsafe_allow_html=True,
        )
        st.button(
            "Reset filters",
            on_click=_reset_filters,
            args=(date_key, default_date_range),
            **full_width_kwargs(st.button),
        )
        if st.button("Refresh data", **full_width_kwargs(st.button)):
            from dashboard.database import refresh_database_cache

            refresh_database_cache()
            st.rerun()

    return DashboardFilters(
        start_date=start_date,
        end_date=end_date,
        states=tuple(states),
        categories=tuple(categories),
        statuses=tuple(statuses),
    )


def _reset_filters(date_key: str, default_date_range: tuple[date, ...]) -> None:
    st.session_state[date_key] = default_date_range
    st.session_state["global_states"] = []
    st.session_state["global_categories"] = []
    st.session_state["global_statuses"] = []


def currency(value: float | int, decimals: int = 0) -> str:
    if pd.isna(value):
        return "R$ —"
    return f"R$ {value:,.{decimals}f}"


def currency_compact(value: float | int, decimals: int = 2) -> str:
    if pd.isna(value):
        return "R$ —"
    abs_value = abs(float(value))
    suffixes = ["", "K", "M", "B"]
    magnitude = 0
    while abs_value >= 1000 and magnitude < len(suffixes) - 1:
        abs_value /= 1000
        magnitude += 1
    return f"R$ {abs_value:,.{decimals}f}{suffixes[magnitude]}"


def number(value: float | int) -> str:
    return f"{value:,.0f}"


def percentage(value: float | int) -> str:
    return f"{value:.1f}%"


def delta_text(current: float, previous: float) -> str:
    if previous == 0:
        return "—" if current == 0 else "New"
    change = (current - previous) / abs(previous) * 100
    return f"{change:+.1f}% vs prior period"


def _as_date(value: Any) -> date | None:
    if not value:
        return None
    return date.fromisoformat(str(value))
