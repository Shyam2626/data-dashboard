import streamlit as st
from auth import require_auth, logout
from modules import REGISTRY

st.set_page_config(page_title="Data Dashboard", page_icon="📊", layout="wide")

require_auth()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"**{st.session_state['user_name']}**")
    st.caption(st.session_state["user_email"])
    st.divider()

    module_name = st.radio("Module", list(REGISTRY.keys()), label_visibility="collapsed")

    st.divider()
    if st.button("Sign out", use_container_width=True):
        logout()

# ── Render active module ──────────────────────────────────────────────────────
REGISTRY[module_name].render()
