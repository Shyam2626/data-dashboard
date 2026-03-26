import streamlit as st
import pandas as pd
from datetime import date, timedelta
from auth import require_auth, logout
from modules import REGISTRY

_PRESETS = {"30D": 30, "3M": 90, "6M": 180, "12M": 365}

st.set_page_config(page_title="Data Dashboard", page_icon="📊", layout="wide")

require_auth()

_NAV = {
    "Billing":   ("💳", "Billing metrics and trends"),
    "Tickets":   ("🎫", "Ticket volume and SLA metrics"),
    "Contracts": ("📄", "Contract coverage and renewals"),
    "RMM":       ("🖥️", "Remote monitoring and management"),
    "Policy":    ("🛡️", "Policy adoption and automation"),
}

if "active_module" not in st.session_state:
    st.session_state["active_module"] = "Billing"

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"**{st.session_state['user_name']}**")
    st.caption(st.session_state["user_email"])
    st.divider()

    items_html = """
<style>
.nav-wrap { margin-bottom: 4px; }
.nav-card {
    display: flex; align-items: center; gap: 12px;
    padding: 11px 14px; border-radius: 10px;
    border: 1px solid #e2e8f0; background: #fff;
    text-decoration: none; color: inherit; cursor: pointer;
}
.nav-card:hover { background: #f1f5f9; border-color: #cbd5e1; }
.nav-card.active {
    background: #eef2ff; border-color: #c7d2fe;
    border-right: 3px solid #4361ee;
}
.nav-icon { font-size: 20px; flex-shrink: 0; }
.nav-name { font-size: 14px; font-weight: 500; color: #334155; line-height: 1.3; }
.nav-card.active .nav-name { font-weight: 600; color: #4361ee; }
.nav-sub  { font-size: 12px; color: #94a3b8; margin-top: 2px; }
</style>
<p style="font-size:11px;font-weight:700;color:#aaa;letter-spacing:1.5px;margin:0 0 10px 0">
DASHBOARD SECTIONS</p>
"""

    for name, (icon, subtitle) in _NAV.items():
        active_class = "active" if st.session_state["active_module"] == name else ""
        if active_class:
            items_html += f"""
<div class="nav-wrap">
  <div class="nav-card active">
    <span class="nav-icon">{icon}</span>
    <div>
      <div class="nav-name">{name}</div>
      <div class="nav-sub">{subtitle}</div>
    </div>
  </div>
</div>"""
        else:
            items_html += f"""
<div class="nav-wrap">
  <a class="nav-card" href="?nav={name}" target="_self">
    <span class="nav-icon">{icon}</span>
    <div>
      <div class="nav-name">{name}</div>
      <div class="nav-sub">{subtitle}</div>
    </div>
  </a>
</div>"""

    st.markdown(items_html, unsafe_allow_html=True)

    # Hidden buttons to handle nav clicks when query param changes
    for name in _NAV:
        if st.query_params.get("nav") == name and st.session_state["active_module"] != name:
            st.session_state["active_module"] = name
            st.query_params.clear()
            st.rerun()

    st.divider()
    if st.button("Sign out", use_container_width=True):
        logout()

# ── Global date filter ────────────────────────────────────────────────────────
col_preset, col_custom = st.columns([3, 2])

with col_preset:
    preset = st.segmented_control(
        "Time range",
        options=list(_PRESETS.keys()) + ["Custom"],
        default="12M",
        key="time_preset",
        label_visibility="collapsed",
    )

end_date = date.today()

if preset == "Custom":
    with col_custom:
        custom_range = st.date_input(
            "Custom range",
            value=(end_date - timedelta(days=365), end_date),
            label_visibility="collapsed",
        )
    if isinstance(custom_range, (tuple, list)) and len(custom_range) == 2:
        start_date, end_date = custom_range[0], custom_range[1]
    else:
        start_date = end_date - timedelta(days=365)
else:
    start_date = end_date - timedelta(days=_PRESETS.get(preset, 365))

st.session_state["filter_start"] = pd.Timestamp(start_date)
st.session_state["filter_end"] = pd.Timestamp(end_date)

st.divider()

# ── Render active module ──────────────────────────────────────────────────────
REGISTRY[st.session_state["active_module"]].render()
