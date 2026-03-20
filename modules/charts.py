"""
Shared chart helpers with per-chart type selector.

Each helper renders a small radio toggle above the chart so the user can
switch between chart types without any page reload.
"""

import re
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# ── Utilities ─────────────────────────────────────────────────────────────────

def _resolve(data, title: str) -> pd.DataFrame:
    """Accept either a DataFrame or a zero-arg callable (query function).
    If callable, run it inside a spinner so users see feedback while waiting."""
    if callable(data):
        with st.spinner(f"Loading {title}..."):
            return data()
    return data


def trim(df: pd.DataFrame) -> pd.DataFrame:
    """Start from the first row with sustained non-zero counts."""
    if df.empty:
        return df
    int_cols = [c for c in df.columns if pd.api.types.is_integer_dtype(df[c])]
    if not int_cols:
        int_cols = list(df.select_dtypes(include="number").columns)
    row_sums = df[int_cols].fillna(0).sum(axis=1)
    peak = row_sums.max()
    if peak == 0:
        return df
    threshold = peak * 0.01
    for i in range(len(df) - 1):
        if row_sums.iloc[i] >= threshold and row_sums.iloc[i + 1] > 0:
            return df.iloc[i:].reset_index(drop=True)
    return df


def _date_filter(df: pd.DataFrame, x: str) -> pd.DataFrame:
    """Apply global date range from session state. Falls back to trim() if not set."""
    start = st.session_state.get("filter_start")
    end = st.session_state.get("filter_end")
    if start is None or end is None or x not in df.columns:
        return trim(df)
    try:
        # Convert via str to handle db-dtypes DATE objects from BigQuery
        col = pd.to_datetime(df[x].astype(str), errors="coerce")
        mask = (col >= pd.Timestamp(start)) & (col <= pd.Timestamp(end))
        return df[mask].reset_index(drop=True)
    except Exception:
        return trim(df)


def _key(title: str) -> str:
    """Stable session-state key from chart title."""
    return "ct_" + re.sub(r"[^a-z0-9]", "_", title.lower())


def _type_selector(title: str, options: list[str]) -> str:
    return st.radio(
        "Chart type",
        options,
        horizontal=True,
        key=_key(title),
        label_visibility="collapsed",
    )


# ── Chart helpers ─────────────────────────────────────────────────────────────

def line(data, x: str, y: str | list, title: str, pct: bool = False) -> None:
    """Line chart with Line / Bar / Area toggle."""
    df = _date_filter(_resolve(data, title), x)
    if df.empty:
        st.caption("No data")
        return
    cols = [y] if isinstance(y, str) else y
    chart_type = _type_selector(title, ["Line", "Bar", "Area"])

    if chart_type == "Line":
        fig = px.line(df, x=x, y=cols, title=title, markers=True)
    elif chart_type == "Bar":
        fig = px.bar(df, x=x, y=cols, title=title, barmode="group")
    else:
        fig = px.area(df, x=x, y=cols, title=title)

    if pct:
        fig.update_yaxes(ticksuffix="%", range=[0, 100])
    fig.update_layout(legend_title_text="", margin=dict(t=40, b=0))
    st.plotly_chart(fig, width="stretch")


def stacked_bar_with_line(
    data, x: str, bars: list[str], line_col: str, title: str
) -> None:
    """Stacked/grouped bar + secondary-axis line, with Stacked / Grouped toggle."""
    df = _date_filter(_resolve(data, title), x)
    if df.empty:
        st.caption("No data")
        return
    chart_type = _type_selector(title, ["Stacked Bar", "Grouped Bar"])

    fig = go.Figure()
    for col in bars:
        fig.add_trace(go.Bar(name=col, x=df[x], y=df[col]))
    fig.add_trace(
        go.Scatter(
            name=line_col, x=df[x], y=df[line_col],
            yaxis="y2", mode="lines+markers", line=dict(color="black", width=2),
        )
    )
    fig.update_layout(
        title=title,
        barmode="stack" if chart_type == "Stacked Bar" else "group",
        yaxis2=dict(overlaying="y", side="right", ticksuffix="%", range=[0, 100]),
        legend_title_text="",
        margin=dict(t=40, b=0),
    )
    st.plotly_chart(fig, width="stretch")


def grouped_bar(
    data, x: str, y: list[str], title: str
) -> None:
    """Grouped/stacked bar (no line overlay), with Grouped / Stacked toggle."""
    df = _resolve(data, title)
    if df.empty:
        st.caption("No data")
        return
    chart_type = _type_selector(title, ["Grouped Bar", "Stacked Bar"])
    fig = px.bar(df, x=x, y=y, title=title,
                 barmode="group" if chart_type == "Grouped Bar" else "stack")
    fig.update_layout(legend_title_text="", margin=dict(t=40, b=0))
    st.plotly_chart(fig, width="stretch")


def stacked_bar_by_category(
    data, x: str, color: str, y: str, title: str
) -> None:
    """Long-format stacked/grouped bar, with Stacked / Grouped toggle."""
    df = _date_filter(_resolve(data, title), x)
    if df.empty:
        st.caption("No data")
        return
    chart_type = _type_selector(title, ["Stacked Bar", "Grouped Bar"])
    fig = px.bar(df, x=x, y=y, color=color, title=title,
                 barmode="stack" if chart_type == "Stacked Bar" else "group")
    fig.update_layout(legend_title_text="", margin=dict(t=40, b=0))
    st.plotly_chart(fig, width="stretch")
