"""
RMM module — queries and charts from gold RMM tables.

Snapshot tables (no month column) render as KPI metric cards.
Time-series tables render as charts via charts.py.
"""

import functools
import streamlit as st
import pandas as pd

from bigquery import run_query, gold
from modules.charts import line, stacked_bar_with_line


# ── Query functions ───────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def _asset_action_usage_rate():
    return run_query(f"SELECT * FROM {gold('rmm_asset_action_usage_rate')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _asset_offline_rate():
    return run_query(f"SELECT * FROM {gold('rmm_asset_offline_rate')}")

@functools.lru_cache(maxsize=1)
def _critical_alert_unresolved_rate():
    return run_query(f"SELECT * FROM {gold('rmm_critical_alert_unresolved_rate')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _it_doc_coverage_rate():
    return run_query(f"SELECT * FROM {gold('rmm_it_doc_coverage_rate')}")

@functools.lru_cache(maxsize=1)
def _mttp_trend():
    return run_query(f"SELECT * FROM {gold('rmm_mttp_trend')}")

@functools.lru_cache(maxsize=1)
def _patch_compliance_rate():
    return run_query(f"SELECT * FROM {gold('rmm_patch_compliance_rate')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _patch_lag():
    return run_query(f"SELECT * FROM {gold('rmm_patch_lag')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _repeat_alert_rate():
    return run_query(f"SELECT * FROM {gold('rmm_repeat_alert_rate')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _software_currency_rate():
    return run_query(f"SELECT * FROM {gold('rmm_software_currency_rate')}")


# ── Snapshot KPI helper ───────────────────────────────────────────────────────

def _kpi(fn, metrics: list[tuple[str, str, str]]) -> None:
    """Render a row of st.metric cards from a single-row snapshot table.

    metrics: list of (column, label, fmt)
      fmt = "pct"  → "12.3%"
          = "int"  → "1,234"
          = "float" → "12.3"
    """
    with st.spinner("Loading..."):
        df = fn()
    if df.empty:
        st.caption("No data")
        return
    row = df.iloc[0]
    cols = st.columns(len(metrics))
    for col, (column, label, fmt) in zip(cols, metrics):
        val = row.get(column)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            display = "—"
        elif fmt == "pct":
            display = f"{float(val):.1f}%"
        elif fmt == "int":
            display = f"{int(val):,}"
        else:
            display = f"{float(val):.1f}"
        col.metric(label, display)


# ── Module entry point ────────────────────────────────────────────────────────

def render() -> None:
    st.header("RMM")

    # ── Asset Health ──────────────────────────────────────────────────────────
    st.subheader("Asset Health")

    st.caption("Fleet offline status (current snapshot)")
    _kpi(_asset_offline_rate, [
        ("total_monitored_assets",      "Monitored Assets",          "int"),
        ("assets_offline",              "Assets Offline",            "int"),
        ("fleet_offline_rate_pct",      "Fleet Offline Rate",        "pct"),
        ("median_msp_offline_rate_pct", "Median MSP Offline Rate",   "pct"),
        ("msps_with_offline_assets",    "MSPs with Offline Assets",  "int"),
    ])

    st.caption("IT documentation coverage (current snapshot)")
    _kpi(_it_doc_coverage_rate, [
        ("total_monitored_assets",            "Monitored Assets",         "int"),
        ("fleet_itdoc_coverage_rate_pct",     "Fleet IT Doc Coverage",    "pct"),
        ("median_msp_itdoc_coverage_rate_pct","Median MSP IT Doc Coverage","pct"),
        ("msps_with_any_itdoc_coverage",      "MSPs with IT Doc",         "int"),
    ])

    st.caption("Software currency (current snapshot)")
    _kpi(_software_currency_rate, [
        ("fleet_software_currency_rate_pct", "Fleet Software Currency",   "pct"),
        ("median_msp_currency_rate_pct",     "Median MSP Currency Rate",  "pct"),
        ("msps_with_pending_updates",        "MSPs with Pending Updates", "int"),
        ("total_assets_with_updates_pending","Assets Pending Updates",    "int"),
    ])

    # ── Asset Actions ─────────────────────────────────────────────────────────
    st.subheader("Asset Actions")
    line(
        _asset_action_usage_rate, "month",
        ["median_action_usage_rate_pct", "avg_action_usage_rate_pct"],
        "Asset Action Usage Rate %", pct=True,
    )

    # ── Alerts ────────────────────────────────────────────────────────────────
    st.subheader("Alerts")
    line(
        _critical_alert_unresolved_rate, "month",
        ["avg_unresolved_rate_pct", "median_unresolved_rate_pct"],
        "Critical Alert Unresolved Rate %", pct=True,
    )
    line(
        _repeat_alert_rate, "month",
        ["avg_repeat_rate_pct", "median_repeat_rate_pct"],
        "Repeat Alert Rate %", pct=True,
    )

    # ── Patching ──────────────────────────────────────────────────────────────
    st.subheader("Patching")
    line(
        _patch_compliance_rate, "month",
        ["median_compliance_rate_pct", "avg_compliance_rate_pct"],
        "Patch Compliance Rate %", pct=True,
    )
    line(
        _patch_compliance_rate, "month",
        ["median_failure_rate_pct", "avg_failure_rate_pct"],
        "Patch Failure Rate %", pct=True,
    )
    line(
        _patch_lag, "month",
        ["avg_patch_lag_days", "median_patch_lag_days"],
        "Patch Lag (days)",
    )

    # ── MTTP Trend ────────────────────────────────────────────────────────────
    st.subheader("MTTP Trend")
    with st.spinner("Loading MTTP Trend..."):
        df_mttp = _mttp_trend()
    if df_mttp.empty:
        st.caption("No data")
    else:
        st.dataframe(df_mttp, use_container_width=True, hide_index=True)
