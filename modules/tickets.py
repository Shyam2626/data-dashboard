"""
Tickets module — queries and charts from gold ticketing tables.
"""

import functools
import streamlit as st

from bigquery import run_query, gold
from modules.charts import line, stacked_bar_with_line, grouped_bar


# ── Query functions ───────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def _created_resolved_ratio():
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
def _frt():
    return run_query(f"SELECT * FROM {gold('ticketing_frt')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _mttr():
    return run_query(f"SELECT * FROM {gold('ticketing_mttr')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _sla_compliance():
    return run_query(f"SELECT * FROM {gold('ticketing_sla_compliance')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _sla_breach_breakdown():
    return run_query(f"SELECT * FROM {gold('ticketing_sla_breach_breakdown')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _runbook_completion():
    return run_query(f"SELECT * FROM {gold('ticketing_runbook_completion')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _runbook_roi():
    return run_query(f"SELECT * FROM {gold('ticketing_runbook_roi')} ORDER BY category")

@functools.lru_cache(maxsize=1)
def _scheduled_ticket_rate():
    return run_query(f"SELECT * FROM {gold('ticketing_scheduled_ticket_rate')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _timer_vs_manual():
    return run_query(f"SELECT * FROM {gold('ticketing_timer_vs_manual')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _internal_note_rate():
    return run_query(f"SELECT * FROM {gold('ticketing_internal_note_rate')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _side_conversation_rate():
    return run_query(f"SELECT * FROM {gold('ticketing_side_conversation_rate')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _worklog_capture_rate():
    return run_query(f"SELECT * FROM {gold('ticketing_worklog_capture_rate')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _activation():
    return run_query(f"""
        SELECT
            DATE_TRUNC(msp_created_date, MONTH)      AS month,
            COUNT(*)                                  AS msps_activated,
            CAST(AVG(days_to_activation) AS FLOAT64)  AS avg_days_to_activation
        FROM {gold('ticketing_activation')}
        WHERE days_to_activation IS NOT NULL
        GROUP BY 1 ORDER BY 1
    """)


# ── Module entry point ────────────────────────────────────────────────────────

def render() -> None:
    st.header("Tickets")

    st.subheader("Activation")
    line(_activation, "month", "avg_days_to_activation", "Avg Days to Ticketing Activation")

    st.subheader("Volume & Throughput")
    stacked_bar_with_line(
        _created_resolved_ratio, "month",
        ["tickets_created", "tickets_resolved"],
        "created_resolved_ratio",
        "Created vs Resolved Tickets",
    )

    st.subheader("Response & Resolution")
    line(_frt, "month", "avg_frt_minutes", "First Response Time (avg minutes)")
    line(_mttr, "month", "avg_mttr_hours", "Mean Time to Resolve (avg hours)")

    st.subheader("SLA")
    line(_sla_compliance, "month", "compliance_rate_pct", "SLA Compliance Rate", pct=True)
    stacked_bar_with_line(
        _sla_breach_breakdown, "month",
        ["first_response_breaches", "resolution_breaches"],
        "breach_rate_pct",
        "SLA Breach Breakdown",
    )

    st.subheader("Runbooks")
    line(_runbook_completion, "month", "completion_rate_pct", "Runbook Completion Rate", pct=True)
    grouped_bar(
        _runbook_roi, "category",
        ["avg_mttr_with_runbook_hours", "avg_mttr_without_runbook_hours"],
        "Runbook ROI — MTTR With vs Without Runbook (hours)",
    )

    st.subheader("Automation & Logging")
    line(_scheduled_ticket_rate, "month", "scheduled_ticket_rate_pct", "Scheduled Ticket Rate", pct=True)
    stacked_bar_with_line(
        _timer_vs_manual, "month",
        ["timer_entries", "manual_entries"],
        "timer_rate_pct",
        "Timer vs Manual Time Entries",
    )
    line(_worklog_capture_rate, "month", "worklog_capture_rate_pct", "Worklog Capture Rate", pct=True)

    st.subheader("Collaboration")
    line(_internal_note_rate, "month", "internal_note_rate_pct", "Internal Note Rate", pct=True)
    line(_side_conversation_rate, "month", "side_conversation_rate_pct", "Side Conversation Rate", pct=True)
