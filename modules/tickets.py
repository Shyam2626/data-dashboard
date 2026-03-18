"""
Tickets module — queries and charts from gold ticketing tables.

To add a new chart:
  1. Write a @functools.lru_cache query function using run_query + gold().
  2. Call it in render() and pass the result to a chart helper.
"""

import functools
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from bigquery import run_query, gold


# ── Query functions ───────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def _created_resolved_ratio() -> pd.DataFrame:
    # Aggregate per-MSP rows up to month level
    return run_query(f"""
        SELECT
            month,
            SUM(tickets_created)  AS tickets_created,
            SUM(tickets_resolved) AS tickets_resolved,
            ROUND(SAFE_DIVIDE(SUM(tickets_created), NULLIF(SUM(tickets_resolved), 0)), 2)
                AS created_resolved_ratio
        FROM {gold('ticketing_created_resolved_ratio')}
        GROUP BY 1 ORDER BY 1
    """)


@functools.lru_cache(maxsize=1)
def _frt() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('ticketing_frt')} ORDER BY month")


@functools.lru_cache(maxsize=1)
def _mttr() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('ticketing_mttr')} ORDER BY month")


@functools.lru_cache(maxsize=1)
def _sla_compliance() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('ticketing_sla_compliance')} ORDER BY month")


@functools.lru_cache(maxsize=1)
def _sla_breach_breakdown() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('ticketing_sla_breach_breakdown')} ORDER BY month")


@functools.lru_cache(maxsize=1)
def _runbook_completion() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('ticketing_runbook_completion')} ORDER BY month")


@functools.lru_cache(maxsize=1)
def _runbook_roi() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('ticketing_runbook_roi')} ORDER BY category")


@functools.lru_cache(maxsize=1)
def _scheduled_ticket_rate() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('ticketing_scheduled_ticket_rate')} ORDER BY month")


@functools.lru_cache(maxsize=1)
def _timer_vs_manual() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('ticketing_timer_vs_manual')} ORDER BY month")


@functools.lru_cache(maxsize=1)
def _internal_note_rate() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('ticketing_internal_note_rate')} ORDER BY month")


@functools.lru_cache(maxsize=1)
def _side_conversation_rate() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('ticketing_side_conversation_rate')} ORDER BY month")


@functools.lru_cache(maxsize=1)
def _worklog_capture_rate() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('ticketing_worklog_capture_rate')} ORDER BY month")


@functools.lru_cache(maxsize=1)
def _activation() -> pd.DataFrame:
    # Aggregate per-MSP rows to monthly avg days-to-activation
    return run_query(f"""
        SELECT
            DATE_TRUNC(msp_created_date, MONTH)      AS month,
            COUNT(*)                                  AS msps_activated,
            CAST(AVG(days_to_activation) AS FLOAT64)  AS avg_days_to_activation
        FROM {gold('ticketing_activation')}
        WHERE days_to_activation IS NOT NULL
        GROUP BY 1 ORDER BY 1
    """)


# ── Chart helpers ─────────────────────────────────────────────────────────────

def _trim(df: pd.DataFrame) -> pd.DataFrame:
    """Start from the first month with sustained non-zero counts."""
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


def _line(df: pd.DataFrame, x: str, y: str | list, title: str, pct: bool = False) -> None:
    df = _trim(df)
    if df.empty:
        st.caption("No data")
        return
    cols = [y] if isinstance(y, str) else y
    fig = px.line(df, x=x, y=cols, title=title, markers=True)
    if pct:
        fig.update_yaxes(ticksuffix="%", range=[0, 100])
    fig.update_layout(legend_title_text="", margin=dict(t=40, b=0))
    st.plotly_chart(fig, width="stretch")


def _stacked_bar_with_line(
    df: pd.DataFrame, x: str, bars: list[str], line: str, title: str
) -> None:
    df = _trim(df)
    if df.empty:
        st.caption("No data")
        return
    fig = go.Figure()
    for col in bars:
        fig.add_trace(go.Bar(name=col, x=df[x], y=df[col]))
    fig.add_trace(
        go.Scatter(
            name=line, x=df[x], y=df[line],
            yaxis="y2", mode="lines+markers", line=dict(color="black", width=2),
        )
    )
    fig.update_layout(
        title=title,
        barmode="stack",
        yaxis2=dict(overlaying="y", side="right", ticksuffix="%", range=[0, 100]),
        legend_title_text="",
        margin=dict(t=40, b=0),
    )
    st.plotly_chart(fig, width="stretch")


def _grouped_bar(df: pd.DataFrame, x: str, y: list[str], title: str) -> None:
    if df.empty:
        st.caption("No data")
        return
    fig = px.bar(df, x=x, y=y, title=title, barmode="group")
    fig.update_layout(legend_title_text="", margin=dict(t=40, b=0))
    st.plotly_chart(fig, width="stretch")


# ── Module entry point ────────────────────────────────────────────────────────

def render() -> None:
    st.header("Tickets")
    
        # ── Activation ────────────────────────────────────────────────────────────
    st.subheader("Activation")
    _line(_activation(), "month", "avg_days_to_activation", "Avg Days to Ticketing Activation")

    # ── Volume & Throughput ───────────────────────────────────────────────────
    st.subheader("Volume & Throughput")
    _stacked_bar_with_line(
        _created_resolved_ratio(), "month",
        ["tickets_created", "tickets_resolved"],
        "created_resolved_ratio",
        "Created vs Resolved Tickets",
    )

    # ── Response & Resolution ─────────────────────────────────────────────────
    st.subheader("Response & Resolution")
    _line(_frt(), "month", "avg_frt_minutes", "First Response Time (avg minutes)")
    _line(_mttr(), "month", "avg_mttr_hours", "Mean Time to Resolve (avg hours)")

    # ── SLA ───────────────────────────────────────────────────────────────────
    st.subheader("SLA")
    _line(_sla_compliance(), "month", "compliance_rate_pct", "SLA Compliance Rate", pct=True)
    _stacked_bar_with_line(
        _sla_breach_breakdown(), "month",
        ["first_response_breaches", "resolution_breaches"],
        "breach_rate_pct",
        "SLA Breach Breakdown",
    )

    # ── Runbooks ──────────────────────────────────────────────────────────────
    st.subheader("Runbooks")
    _line(_runbook_completion(), "month", "completion_rate_pct", "Runbook Completion Rate", pct=True)
    _grouped_bar(
        _runbook_roi(), "category",
        ["avg_mttr_with_runbook_hours", "avg_mttr_without_runbook_hours"],
        "Runbook ROI — MTTR With vs Without Runbook (hours)",
    )

    # ── Automation & Logging ──────────────────────────────────────────────────
    st.subheader("Automation & Logging")
    _line(_scheduled_ticket_rate(), "month", "scheduled_ticket_rate_pct", "Scheduled Ticket Rate", pct=True)
    _stacked_bar_with_line(
        _timer_vs_manual(), "month",
        ["timer_entries", "manual_entries"],
        "timer_rate_pct",
        "Timer vs Manual Time Entries",
    )
    _line(_worklog_capture_rate(), "month", "worklog_capture_rate_pct", "Worklog Capture Rate", pct=True)

    # ── Collaboration ─────────────────────────────────────────────────────────
    st.subheader("Collaboration")
    _line(_internal_note_rate(), "month", "internal_note_rate_pct", "Internal Note Rate", pct=True)
    _line(_side_conversation_rate(), "month", "side_conversation_rate_pct", "Side Conversation Rate", pct=True)
