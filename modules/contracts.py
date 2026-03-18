"""
Contracts module — queries and charts from gold contracts tables.

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
def _active_msp_coverage() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('contracts_active_msp_coverage')} ORDER BY month")


@functools.lru_cache(maxsize=1)
def _avg_value_by_msp_size() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('contracts_avg_value_by_msp_size')} ORDER BY month")


@functools.lru_cache(maxsize=1)
def _billable_work_under_contract() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('contracts_billable_work_under_contract')} ORDER BY billing_cycle")


@functools.lru_cache(maxsize=1)
def _duration_distribution() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('contracts_duration_distribution')} ORDER BY month, duration_bucket")


@functools.lru_cache(maxsize=1)
def _per_client_avg() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('contracts_per_client_avg')} ORDER BY month")


@functools.lru_cache(maxsize=1)
def _pricing_type_distribution() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('contracts_pricing_type_distribution')} ORDER BY month")


@functools.lru_cache(maxsize=1)
def _renewal_alert_adoption() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('contracts_renewal_alert_adoption')} ORDER BY month")


@functools.lru_cache(maxsize=1)
def _renewal_rate() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('contracts_renewal_rate')} ORDER BY month")


@functools.lru_cache(maxsize=1)
def _sla_assignment_rate() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('contracts_sla_assignment_rate')} ORDER BY month")


@functools.lru_cache(maxsize=1)
def _template_usage_rate() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('contracts_template_usage_rate')} ORDER BY month")


@functools.lru_cache(maxsize=1)
def _type_distribution() -> pd.DataFrame:
    return run_query(f"SELECT * FROM {gold('contracts_type_distribution')} ORDER BY month")


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


def _stacked_bar_by_category(
    df: pd.DataFrame, x: str, color: str, y: str, title: str
) -> None:
    """Stacked bar where rows are long-format (x, color, y)."""
    df = _trim(df)
    if df.empty:
        st.caption("No data")
        return
    fig = px.bar(df, x=x, y=y, color=color, title=title, barmode="stack")
    fig.update_layout(legend_title_text="", margin=dict(t=40, b=0))
    st.plotly_chart(fig, width="stretch")


# ── Module entry point ────────────────────────────────────────────────────────

def render() -> None:
    st.header("Contracts")

    # ── Coverage & Adoption ───────────────────────────────────────────────────
    st.subheader("Coverage & Adoption")
    _line(_active_msp_coverage(), "month", "coverage_rate_pct", "Active MSP Contract Coverage", pct=True)
    _line(_renewal_alert_adoption(), "month", "renewal_alert_adoption_pct", "Renewal Alert Adoption", pct=True)

    # ── Renewals ──────────────────────────────────────────────────────────────
    st.subheader("Renewals")
    _stacked_bar_with_line(
        _renewal_rate(), "month",
        ["contracts_renewed", "contracts_not_renewed"],
        "renewal_rate_pct",
        "Contract Renewal Rate",
    )

    # ── Contract Mix ──────────────────────────────────────────────────────────
    st.subheader("Contract Mix")
    _stacked_bar_with_line(
        _pricing_type_distribution(), "month",
        ["fixed_contracts", "dynamic_contracts"],
        "fixed_pct",
        "Pricing Type Distribution (Fixed vs Dynamic)",
    )
    _stacked_bar_by_category(
        _duration_distribution(), "month", "duration_bucket", "contract_count",
        "Contract Duration Distribution",
    )
    _stacked_bar_with_line(
        _type_distribution(), "month",
        ["service_contracts", "usage_contracts", "time_and_material_contracts", "one_time_contracts"],
        "service_pct",
        "Contract Type Distribution",
    )

    # ── Value & Usage ─────────────────────────────────────────────────────────
    st.subheader("Value & Usage")
    _line(_avg_value_by_msp_size(), "month", "avg_contract_mrr", "Avg Contract MRR")
    _line(_per_client_avg(), "month", "avg_contracts_per_client", "Avg Contracts per Client")
    _stacked_bar_with_line(
        _billable_work_under_contract(), "billing_cycle",
        ["items_under_contract", "items_without_contract"],
        "under_contract_rate_pct",
        "Billable Work Under Contract",
    )
    _stacked_bar_with_line(
        _template_usage_rate(), "month",
        ["from_template", "from_scratch"],
        "template_usage_rate_pct",
        "Contract Template Usage",
    )

    # ── Quality ───────────────────────────────────────────────────────────────
    st.subheader("Quality")
    _line(_sla_assignment_rate(), "month", "sla_assignment_rate_pct", "SLA Assignment Rate", pct=True)
