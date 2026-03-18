"""
Billing module — queries and charts.

All metrics read from pre-aggregated gold tables.

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
def _accounting_sync_success() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('billing_accounting_sync_success')} ORDER BY billing_cycle")


@functools.lru_cache(maxsize=1)
def _active_msp_adoption() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('billing_active_msp_adoption')} ORDER BY billing_cycle")


@functools.lru_cache(maxsize=1)
def _auto_generated_invoice_pct() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('billing_auto_generated_invoice_pct')} ORDER BY billing_cycle")


@functools.lru_cache(maxsize=1)
def _billing_queue_completion() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('billing_billing_queue_completion')} ORDER BY billing_cycle")


@functools.lru_cache(maxsize=1)
def _dso() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('billing_dso')} ORDER BY billing_cycle")


@functools.lru_cache(maxsize=1)
def _overdue_invoice_ratio() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('billing_overdue_invoice_ratio')} ORDER BY billing_cycle")


@functools.lru_cache(maxsize=1)
def _sync_error_rate() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('billing_sync_error_rate')} ORDER BY billing_cycle")


@functools.lru_cache(maxsize=1)
def _cycle_retention() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('billing_cycle_retention')} ORDER BY billing_cycle")


@functools.lru_cache(maxsize=1)
def _schedule_adoption() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('billing_schedule_adoption')} ORDER BY billing_cycle")


@functools.lru_cache(maxsize=1)
def _reminder_setup_rate() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('billing_reminder_setup_rate')} ORDER BY billing_cycle")


# ── Chart helpers ─────────────────────────────────────────────────────────────

def _trim(df: pd.DataFrame, x: str) -> pd.DataFrame:
    """Start from the first date with sustained non-zero counts; show all data up to today."""
    if df.empty:
        return df
    # Use integer count columns only — excludes pct floats that skew the threshold
    int_cols = [c for c in df.columns if pd.api.types.is_integer_dtype(df[c])]
    if not int_cols:
        int_cols = list(df.select_dtypes(include="number").columns)
    row_sums = df[int_cols].fillna(0).sum(axis=1)
    peak = row_sums.max()
    if peak == 0:
        return df
    # Find first row where counts reach 1% of peak AND the next row is also non-zero
    # — this skips isolated early test data points (e.g. 1–2 MSPs in 2018)
    threshold = peak * 0.01
    for i in range(len(df) - 1):
        if row_sums.iloc[i] >= threshold and row_sums.iloc[i + 1] > 0:
            return df.iloc[i:].reset_index(drop=True)
    return df


def _line(df: pd.DataFrame, x: str, y: str | list, title: str, pct: bool = False) -> None:
    df = _trim(df, x)
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
    df = _trim(df, x)
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


# ── Module entry point ────────────────────────────────────────────────────────

def render() -> None:
    st.header("Billing")

    # ── Adoption & Retention ──────────────────────────────────────────────────
    st.subheader("Adoption & Retention")
    _line(_active_msp_adoption(), "billing_cycle", ["billing_msps", "active_msps"], "Active MSP Adoption")
    _line(_cycle_retention(), "billing_cycle", "retention_rate_pct", "Cycle Retention Rate", pct=True)
    _line(_schedule_adoption(), "billing_cycle", "schedule_adoption_pct", "Schedule Adoption", pct=True)

    # ── Invoice Automation ────────────────────────────────────────────────────
    st.subheader("Invoice Automation")
    _line(_auto_generated_invoice_pct(), "billing_cycle", "auto_generated_pct", "Auto-Generated Invoice %", pct=True)
    _line(_billing_queue_completion(), "billing_cycle", "completion_rate_pct", "Billing Queue Completion %", pct=True)
    _line(_reminder_setup_rate(), "billing_cycle", "reminder_setup_rate_pct", "Reminder Setup Rate", pct=True)

    # ── Payment Health ────────────────────────────────────────────────────────
    st.subheader("Payment Health")
    _line(_dso(), "billing_cycle", ["median_dso_days", "p75_dso_days", "p90_dso_days"], "Days Sales Outstanding")
    _stacked_bar_with_line(
        _overdue_invoice_ratio(), "billing_cycle",
        ["overdue_1_30", "overdue_31_60", "overdue_61_90", "overdue_90plus"],
        "overdue_ratio_pct",
        "Overdue Invoice Breakdown",
    )

    # ── Sync & Accounting ─────────────────────────────────────────────────────
    st.subheader("Sync & Accounting")
    _line(_accounting_sync_success(), "billing_cycle", "sync_success_rate_pct", "Accounting Sync Success %", pct=True)
    _line(_sync_error_rate(), "billing_cycle", "sync_error_rate_pct", "Sync Error Rate %", pct=True)
