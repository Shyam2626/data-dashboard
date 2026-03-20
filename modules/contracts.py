"""
Contracts module — queries and charts from gold contracts tables.
"""

import functools
import streamlit as st

from bigquery import run_query, gold
from modules.charts import line, stacked_bar_with_line, grouped_bar, stacked_bar_by_category


# ── Query functions ───────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def _active_msp_coverage():
    return run_query(f"SELECT * FROM {gold('contracts_active_msp_coverage')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _avg_value_by_msp_size():
    return run_query(f"SELECT * FROM {gold('contracts_avg_value_by_msp_size')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _billable_work_under_contract():
    return run_query(f"SELECT * FROM {gold('contracts_billable_work_under_contract')} ORDER BY billing_cycle")

@functools.lru_cache(maxsize=1)
def _duration_distribution():
    return run_query(f"SELECT * FROM {gold('contracts_duration_distribution')} ORDER BY month, duration_bucket")

@functools.lru_cache(maxsize=1)
def _per_client_avg():
    return run_query(f"SELECT * FROM {gold('contracts_per_client_avg')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _pricing_type_distribution():
    return run_query(f"SELECT * FROM {gold('contracts_pricing_type_distribution')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _renewal_alert_adoption():
    return run_query(f"SELECT * FROM {gold('contracts_renewal_alert_adoption')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _renewal_rate():
    return run_query(f"SELECT * FROM {gold('contracts_renewal_rate')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _sla_assignment_rate():
    return run_query(f"SELECT * FROM {gold('contracts_sla_assignment_rate')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _template_usage_rate():
    return run_query(f"SELECT * FROM {gold('contracts_template_usage_rate')} ORDER BY month")

@functools.lru_cache(maxsize=1)
def _type_distribution():
    return run_query(f"SELECT * FROM {gold('contracts_type_distribution')} ORDER BY month")


# ── Module entry point ────────────────────────────────────────────────────────

def render() -> None:
    st.header("Contracts")

    st.subheader("Coverage & Adoption")
    line(_active_msp_coverage, "month", "coverage_rate_pct", "Active MSP Contract Coverage", pct=True)
    line(_renewal_alert_adoption, "month", "renewal_alert_adoption_pct", "Renewal Alert Adoption", pct=True)

    st.subheader("Renewals")
    stacked_bar_with_line(
        _renewal_rate, "month",
        ["contracts_renewed", "contracts_not_renewed"],
        "renewal_rate_pct",
        "Contract Renewal Rate",
    )

    st.subheader("Contract Mix")
    stacked_bar_with_line(
        _pricing_type_distribution, "month",
        ["fixed_contracts", "dynamic_contracts"],
        "fixed_pct",
        "Pricing Type Distribution (Fixed vs Dynamic)",
    )
    stacked_bar_by_category(
        _duration_distribution, "month", "duration_bucket", "contract_count",
        "Contract Duration Distribution",
    )
    stacked_bar_with_line(
        _type_distribution, "month",
        ["service_contracts", "usage_contracts", "time_and_material_contracts", "one_time_contracts"],
        "service_pct",
        "Contract Type Distribution",
    )

    st.subheader("Value & Usage")
    line(_avg_value_by_msp_size, "month", "avg_contract_mrr", "Avg Contract MRR")
    line(_per_client_avg, "month", "avg_contracts_per_client", "Avg Contracts per Client")
    stacked_bar_with_line(
        _billable_work_under_contract, "billing_cycle",
        ["items_under_contract", "items_without_contract"],
        "under_contract_rate_pct",
        "Billable Work Under Contract",
    )
    stacked_bar_with_line(
        _template_usage_rate, "month",
        ["from_template", "from_scratch"],
        "template_usage_rate_pct",
        "Contract Template Usage",
    )

    st.subheader("Quality")
    line(_sla_assignment_rate, "month", "sla_assignment_rate_pct", "SLA Assignment Rate", pct=True)
