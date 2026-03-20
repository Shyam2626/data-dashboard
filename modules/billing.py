"""
Billing module — queries and charts from gold billing tables.
"""

import functools
import streamlit as st

from bigquery import run_query, gold
from modules.charts import line, stacked_bar_with_line


# ── Query functions ───────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def _accounting_sync_success():
    return run_query(f"SELECT * FROM {gold('billing_accounting_sync_success')} ORDER BY billing_cycle")

@functools.lru_cache(maxsize=1)
def _active_msp_adoption():
    return run_query(f"SELECT * FROM {gold('billing_active_msp_adoption')} ORDER BY billing_cycle")

@functools.lru_cache(maxsize=1)
def _auto_generated_invoice_pct():
    return run_query(f"SELECT * FROM {gold('billing_auto_generated_invoice_pct')} ORDER BY billing_cycle")

@functools.lru_cache(maxsize=1)
def _billing_queue_completion():
    return run_query(f"SELECT * FROM {gold('billing_billing_queue_completion')} ORDER BY billing_cycle")

@functools.lru_cache(maxsize=1)
def _dso():
    return run_query(f"SELECT * FROM {gold('billing_dso')} ORDER BY billing_cycle")

@functools.lru_cache(maxsize=1)
def _overdue_invoice_ratio():
    return run_query(f"SELECT * FROM {gold('billing_overdue_invoice_ratio')} ORDER BY billing_cycle")

@functools.lru_cache(maxsize=1)
def _sync_error_rate():
    return run_query(f"SELECT * FROM {gold('billing_sync_error_rate')} ORDER BY billing_cycle")

@functools.lru_cache(maxsize=1)
def _cycle_retention():
    return run_query(f"SELECT * FROM {gold('billing_cycle_retention')} ORDER BY billing_cycle")

@functools.lru_cache(maxsize=1)
def _schedule_adoption():
    return run_query(f"SELECT * FROM {gold('billing_schedule_adoption')} ORDER BY billing_cycle")

@functools.lru_cache(maxsize=1)
def _reminder_setup_rate():
    return run_query(f"SELECT * FROM {gold('billing_reminder_setup_rate')} ORDER BY billing_cycle")


# ── Module entry point ────────────────────────────────────────────────────────

def render() -> None:
    st.header("Billing")

    st.subheader("Adoption & Retention")
    line(_active_msp_adoption, "billing_cycle", ["billing_msps", "active_msps"], "Active MSP Adoption")
    line(_cycle_retention, "billing_cycle", "retention_rate_pct", "Cycle Retention Rate", pct=True)
    line(_schedule_adoption, "billing_cycle", "schedule_adoption_pct", "Schedule Adoption", pct=True)

    st.subheader("Invoice Automation")
    line(_auto_generated_invoice_pct, "billing_cycle", "auto_generated_pct", "Auto-Generated Invoice %", pct=True)
    line(_billing_queue_completion, "billing_cycle", "completion_rate_pct", "Billing Queue Completion %", pct=True)
    line(_reminder_setup_rate, "billing_cycle", "reminder_setup_rate_pct", "Reminder Setup Rate", pct=True)

    st.subheader("Payment Health")
    line(_dso, "billing_cycle", ["median_dso_days", "p75_dso_days", "p90_dso_days"], "Days Sales Outstanding")
    stacked_bar_with_line(
        _overdue_invoice_ratio, "billing_cycle",
        ["overdue_1_30", "overdue_31_60", "overdue_61_90", "overdue_90plus"],
        "overdue_ratio_pct",
        "Overdue Invoice Breakdown",
    )

    st.subheader("Sync & Accounting")
    line(_accounting_sync_success, "billing_cycle", "sync_success_rate_pct", "Accounting Sync Success %", pct=True)
    line(_sync_error_rate, "billing_cycle", "sync_error_rate_pct", "Sync Error Rate %", pct=True)
