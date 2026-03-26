"""
Policy module — queries and charts from gold policy tables.

Snapshot tables (no time column) render as KPI metric cards.
Quarterly time-series tables render as charts via charts.py.
Categorical tables render as bar charts or dataframes.
"""

import functools
import streamlit as st
import pandas as pd

from bigquery import run_query, gold
from modules.charts import line, stacked_bar_with_line, grouped_bar


# ── Query functions ────────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def _alert_activation():
    return run_query(f"SELECT * FROM {gold('policy_alert_activation')}")

@functools.lru_cache(maxsize=1)
def _auto_resolved_issues():
    return run_query(f"SELECT * FROM {gold('policy_auto_resolved_issues')} ORDER BY quarter")

@functools.lru_cache(maxsize=1)
def _automation_maturity():
    return run_query(f"SELECT * FROM {gold('policy_automation_maturity')}")

@functools.lru_cache(maxsize=1)
def _av_adoption():
    return run_query(f"SELECT * FROM {gold('policy_av_adoption')}")

@functools.lru_cache(maxsize=1)
def _av_platform_distribution():
    return run_query(f"SELECT * FROM {gold('policy_av_platform_distribution')} ORDER BY msp_count DESC")

@functools.lru_cache(maxsize=1)
def _avg_policies():
    return run_query(f"SELECT * FROM {gold('policy_avg_policies')}")

@functools.lru_cache(maxsize=1)
def _coverage_growth():
    return run_query(f"SELECT * FROM {gold('policy_coverage_growth')} ORDER BY quarter")

@functools.lru_cache(maxsize=1)
def _critical_coverage():
    return run_query(f"SELECT * FROM {gold('policy_critical_coverage')}")

@functools.lru_cache(maxsize=1)
def _maintenance_mode_usage():
    return run_query(f"SELECT * FROM {gold('policy_maintenance_mode_usage')}")

@functools.lru_cache(maxsize=1)
def _onboarding_automation():
    return run_query(f"SELECT * FROM {gold('policy_onboarding_automation')}")

@functools.lru_cache(maxsize=1)
def _patch_approval_automation():
    return run_query(f"SELECT * FROM {gold('policy_patch_approval_automation')} ORDER BY quarter")

@functools.lru_cache(maxsize=1)
def _patch_approval_workflow():
    return run_query(f"SELECT * FROM {gold('policy_patch_approval_workflow')}")

@functools.lru_cache(maxsize=1)
def _patch_schedule_adoption():
    return run_query(f"SELECT * FROM {gold('policy_patch_schedule_adoption')}")

@functools.lru_cache(maxsize=1)
def _remote_access_adoption():
    return run_query(f"SELECT * FROM {gold('policy_remote_access_adoption')}")

@functools.lru_cache(maxsize=1)
def _scheduled_script_usage():
    return run_query(f"SELECT * FROM {gold('policy_scheduled_script_usage')}")

@functools.lru_cache(maxsize=1)
def _software_mgmt_adoption():
    return run_query(f"SELECT * FROM {gold('policy_software_mgmt_adoption')}")

@functools.lru_cache(maxsize=1)
def _time_to_first_policy():
    return run_query(f"SELECT * FROM {gold('policy_time_to_first_policy')} ORDER BY msp_created_date")

@functools.lru_cache(maxsize=1)
def _top_manual_patch_types():
    return run_query(f"SELECT * FROM {gold('policy_top_manual_patch_types')} ORDER BY manual_approval_pct DESC")


# ── Snapshot KPI helper ────────────────────────────────────────────────────────

def _kpi(fn, metrics: list[tuple[str, str, str]]) -> None:
    """Render a row of st.metric cards from a single-row snapshot table.

    metrics: list of (column, label, fmt)
      fmt = "pct"   → "12.3%"
          = "int"   → "1,234"
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


# ── Module entry point ─────────────────────────────────────────────────────────

def render() -> None:
    st.header("Policy")

    # ── Coverage ──────────────────────────────────────────────────────────────
    st.subheader("Coverage")

    st.caption("Critical policy coverage (current snapshot)")
    _kpi(_critical_coverage, [
        ("total_active_msps",       "Active MSPs",          "int"),
        ("msps_with_alert_policy",  "With Alert Policy",    "int"),
        ("msps_with_patch_policy",  "With Patch Policy",    "int"),
        ("msps_with_av_policy",     "With AV Policy",       "int"),
        ("msps_with_remote_policy", "With Remote Policy",   "int"),
        ("msps_with_all_four",      "All Four Policies",    "int"),
        ("critical_coverage_pct",   "Critical Coverage",    "pct"),
    ])

    st.caption("Average policies per MSP (current snapshot)")
    _kpi(_avg_policies, [
        ("msps_with_active_policies", "MSPs with Policies",   "int"),
        ("avg_policies_per_msp",      "Avg Policies/MSP",     "float"),
        ("median_policies_per_msp",   "Median Policies/MSP",  "float"),
        ("p90_policies_per_msp",      "P90 Policies/MSP",     "float"),
        ("max_policies_per_msp",      "Max Policies/MSP",     "int"),
    ])

    stacked_bar_with_line(
        _coverage_growth, "quarter",
        bars=["new_msps_with_full_coverage"],
        line_col="qoq_growth_pct",
        title="Full Coverage Growth (new MSPs per quarter vs QoQ %)",
    )

    # ── Policy Adoption ───────────────────────────────────────────────────────
    st.subheader("Policy Adoption")

    st.caption("Alert & AV adoption (current snapshot)")
    _kpi(_alert_activation, [
        ("total_active_msps",            "Active MSPs",          "int"),
        ("msps_with_active_alert_rules", "With Alert Rules",     "int"),
        ("alert_activation_rate_pct",    "Alert Activation Rate","pct"),
    ])

    _kpi(_av_adoption, [
        ("total_active_msps",   "Active MSPs",   "int"),
        ("msps_with_av_policy", "With AV Policy","int"),
        ("av_adoption_pct",     "AV Adoption",   "pct"),
    ])

    st.caption("Patch, remote access & software management (current snapshot)")
    _kpi(_patch_schedule_adoption, [
        ("total_active_msps",       "Active MSPs",           "int"),
        ("msps_with_patch_schedule","With Patch Schedule",   "int"),
        ("patch_schedule_adoption_pct", "Patch Schedule Adoption", "pct"),
    ])

    _kpi(_remote_access_adoption, [
        ("total_active_msps",       "Active MSPs",          "int"),
        ("msps_with_remote_policy", "With Remote Policy",   "int"),
        ("remote_access_adoption_pct", "Remote Access Adoption", "pct"),
    ])

    _kpi(_software_mgmt_adoption, [
        ("total_active_msps",        "Active MSPs",              "int"),
        ("msps_with_software_mgmt",  "With Software Mgmt",       "int"),
        ("software_mgmt_adoption_pct","Software Mgmt Adoption",  "pct"),
    ])

    st.caption("Automation & scripting (current snapshot)")
    _kpi(_maintenance_mode_usage, [
        ("total_active_msps",           "Active MSPs",              "int"),
        ("msps_with_maintenance_mode",  "With Maintenance Mode",    "int"),
        ("maintenance_mode_usage_pct",  "Maintenance Mode Usage",   "pct"),
    ])

    _kpi(_scheduled_script_usage, [
        ("total_active_msps",           "Active MSPs",              "int"),
        ("msps_with_scheduled_scripts", "With Scheduled Scripts",   "int"),
        ("scheduled_script_usage_pct",  "Scheduled Script Usage",   "pct"),
    ])

    _kpi(_onboarding_automation, [
        ("total_active_msps",               "Active MSPs",              "int"),
        ("msps_with_onboarding_automation", "With Onboarding Automation","int"),
        ("onboarding_automation_pct",       "Onboarding Automation",    "pct"),
    ])

    st.caption("Policy type diversity (current snapshot)")
    _kpi(_automation_maturity, [
        ("msp_count",          "MSPs",                "int"),
        ("avg_policy_types",   "Avg Policy Types",    "float"),
        ("median_policy_types","Median Policy Types", "float"),
        ("max_policy_types",   "Max Policy Types",    "int"),
    ])

    # ── Antivirus ─────────────────────────────────────────────────────────────
    st.subheader("Antivirus")

    grouped_bar(
        _av_platform_distribution, "av_vendor",
        ["msp_count"],
        "AV Platform Distribution (MSP count by vendor)",
    )

    with st.spinner("Loading AV platform distribution..."):
        df_av = _av_platform_distribution()
    if not df_av.empty:
        st.dataframe(df_av, use_container_width=True, hide_index=True)

    # ── Patching ──────────────────────────────────────────────────────────────
    st.subheader("Patching")

    st.caption("Patch approval workflow (current snapshot)")
    _kpi(_patch_approval_workflow, [
        ("total_patch_policies",          "Total Patch Policies",   "int"),
        ("policies_with_approval_workflow","With Approval Workflow", "int"),
        ("approval_workflow_rate_pct",    "Approval Workflow Rate", "pct"),
    ])

    line(
        _patch_approval_automation, "quarter",
        ["avg_auto_approval_pct", "median_auto_approval_pct"],
        "Patch Auto-Approval Rate % by Quarter", pct=True,
    )

    st.caption("Top manual patch types")
    with st.spinner("Loading top manual patch types..."):
        df_patches = _top_manual_patch_types()
    if df_patches.empty:
        st.caption("No data")
    else:
        st.dataframe(df_patches, use_container_width=True, hide_index=True)

    # ── Automation ────────────────────────────────────────────────────────────
    st.subheader("Automation")

    line(
        _auto_resolved_issues, "quarter",
        ["avg_auto_resolved_per_msp"],
        "Avg Auto-Resolved Issues per MSP by Quarter",
    )

    # ── Onboarding ────────────────────────────────────────────────────────────
    st.subheader("Onboarding")

    st.caption("Time to first policy (per MSP)")
    with st.spinner("Loading time to first policy..."):
        df_onboard = _time_to_first_policy()
    if df_onboard.empty:
        st.caption("No data")
    else:
        st.dataframe(df_onboard, use_container_width=True, hide_index=True)
