import os
import json
import hashlib
import base64
import secrets
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import extra_streamlit_components as stx
import streamlit as st
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from dotenv import load_dotenv

load_dotenv()

ALLOWED_DOMAIN = "superops.com"
GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
REDIRECT_URI = os.environ.get("REDIRECT_URI", "http://localhost:8501")
SESSION_DURATION_HOURS = int(os.environ.get("SESSION_DURATION_HOURS", 8))

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# File-based session store — persists across hot-reloads and process restarts
_SESSIONS_FILE = Path(tempfile.gettempdir()) / "streamlit_dashboard_sessions.json"
_file_lock = threading.Lock()


# ── File-backed session store ─────────────────────────────────────────────────

def _load_sessions() -> dict:
    with _file_lock:
        if not _SESSIONS_FILE.exists():
            return {}
        try:
            return json.loads(_SESSIONS_FILE.read_text())
        except Exception:
            return {}


def _save_sessions(sessions: dict) -> None:
    with _file_lock:
        _SESSIONS_FILE.write_text(json.dumps(sessions))


def _create_session(email: str, name: str) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_DURATION_HOURS)
    sessions = _load_sessions()
    sessions[token] = {
        "email": email,
        "name": name,
        "expires_at": expires_at.isoformat(),
    }
    _save_sessions(sessions)
    return token, expires_at


def _validate_session(token: str) -> dict | None:
    sessions = _load_sessions()
    session = sessions.get(token)
    if not session:
        return None
    expires_at = datetime.fromisoformat(session["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        sessions.pop(token, None)
        _save_sessions(sessions)
        return None
    return session


def _destroy_session(token: str) -> None:
    sessions = _load_sessions()
    sessions.pop(token, None)
    _save_sessions(sessions)


# ── Cookie manager (write/delete only) ───────────────────────────────────────

def _cookie_manager() -> stx.CookieManager:
    if "cookie_manager" not in st.session_state:
        st.session_state["cookie_manager"] = stx.CookieManager(key="auth_cookie_manager")
    return st.session_state["cookie_manager"]


def _get_cookie(name: str) -> str | None:
    return st.context.cookies.get(name)


def _set_cookie(name: str, value: str, expires_at: datetime) -> None:
    _cookie_manager().set(name, value, expires_at=expires_at)


def _delete_cookie(name: str) -> None:
    _cookie_manager().delete(name)


# ── OAuth / PKCE ──────────────────────────────────────────────────────────────

def _build_flow() -> Flow:
    return Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )


def _make_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    return verifier, challenge


def login_button() -> None:
    flow = _build_flow()
    verifier, challenge = _make_pkce_pair()
    state_payload = base64.urlsafe_b64encode(
        json.dumps({"nonce": secrets.token_hex(8), "v": verifier}).encode()
    ).decode()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="select_account",
        state=state_payload,
        code_challenge=challenge,
        code_challenge_method="S256",
    )
    st.link_button("Sign in with Google", auth_url, use_container_width=True)


def handle_oauth_callback() -> bool:
    code = st.query_params.get("code")
    state = st.query_params.get("state")

    if not code or not state:
        return False

    try:
        payload = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
        verifier = payload["v"]
    except Exception:
        st.error("Invalid login state. Please try signing in again.")
        st.query_params.clear()
        return False

    flow = _build_flow()
    flow.fetch_token(code=code, code_verifier=verifier)

    token = flow.credentials.id_token
    user_info = id_token.verify_oauth2_token(
        token, google_requests.Request(), GOOGLE_CLIENT_ID
    )

    email: str = user_info.get("email", "")
    if not email.endswith(f"@{ALLOWED_DOMAIN}"):
        st.error(f"Access denied. Only @{ALLOWED_DOMAIN} accounts are allowed.")
        st.query_params.clear()
        return False

    name = user_info.get("name", email)
    session_token, expires_at = _create_session(email, name)

    # Set cookie first so JS runs during this render, then update session state.
    # Do NOT call st.rerun() here — it interrupts rendering before the cookie
    # JS executes in the browser, so the cookie would never be set.
    _set_cookie("session_token", session_token, expires_at)
    st.session_state["authenticated"] = True
    st.session_state["user_email"] = email
    st.session_state["user_name"] = name
    st.query_params.clear()
    return True


# ── Public API ────────────────────────────────────────────────────────────────

def is_authenticated() -> bool:
    return st.session_state.get("authenticated", False)


def logout() -> None:
    token = _get_cookie("session_token")
    if token:
        _destroy_session(token)
        _delete_cookie("session_token")
    for key in ("authenticated", "user_email", "user_name"):
        st.session_state.pop(key, None)
    st.rerun()


def require_auth() -> None:
    """Call this at the top of every page."""
    # 1. Already authenticated in this browser session
    if is_authenticated():
        return

    # 2. Returning visitor — validate cookie against file-backed session store
    token = _get_cookie("session_token")
    if token:
        session = _validate_session(token)
        if session:
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = session["email"]
            st.session_state["user_name"] = session["name"]
            return

    # 3. Incoming OAuth callback — authenticate and let the page render
    #    (no st.rerun() so the cookie-setting JS executes in this render)
    if st.query_params.get("code"):
        if handle_oauth_callback():
            return

    # 4. Not authenticated — show login
    _show_login_page()
    st.stop()


def _show_login_page() -> None:
    col = st.columns([1, 2, 1])[1]
    with col:
        st.title("Data Dashboard")
        st.markdown(
            f"Sign in with your **@{ALLOWED_DOMAIN}** Google account to continue."
        )
        st.caption(f"Session stays active for {SESSION_DURATION_HOURS} hours.")
        st.divider()
        login_button()
