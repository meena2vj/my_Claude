"""Sidebar login + role resolution.

Users and roles come only from the APP_USERS_JSON environment variable (see
.env.example) -- never hardcoded, per CLAUDE.md's secrets-handling guardrail.
This is a demo-grade auth mechanism (sha256, no lockout/rate-limiting) and is
explicitly documented as such in docs/model_card.md; it is not intended for
anything beyond a local/internal demo.
"""
import hashlib
import json
import os

import streamlit as st

from utils.audit import log_event


def _load_user_map() -> dict:
    raw = os.getenv("APP_USERS_JSON")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _check_credentials(username: str, password: str, user_map: dict) -> str | None:
    user = user_map.get(username)
    if not user:
        return None
    if _hash(password) == user.get("password_sha256"):
        return user.get("role")
    return None


def require_login() -> tuple[str, str]:
    """Blocks (via st.stop()) until a valid login is present in session state.
    Returns (username, role) once authenticated."""
    if "auth_user" in st.session_state and "auth_role" in st.session_state:
        return st.session_state["auth_user"], st.session_state["auth_role"]

    user_map = _load_user_map()

    st.sidebar.subheader("Sign in")
    if not user_map:
        st.sidebar.error("APP_USERS_JSON is not set. Copy .env.example to .env and set it.")
        st.stop()

    with st.sidebar.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if not submitted:
        st.info("Please log in from the sidebar to view this application.")
        st.stop()

    role = _check_credentials(username, password, user_map)
    if not role:
        st.sidebar.error("Invalid username or password.")
        log_event(username or "unknown", "unauthenticated", "failed_login")
        st.stop()

    st.session_state["auth_user"] = username
    st.session_state["auth_role"] = role
    log_event(username, role, "login")
    st.rerun()


def logout() -> None:
    username = st.session_state.get("auth_user", "unknown")
    role = st.session_state.get("auth_role", "unknown")
    log_event(username, role, "logout")
    for key in ("auth_user", "auth_role"):
        st.session_state.pop(key, None)
    st.rerun()
