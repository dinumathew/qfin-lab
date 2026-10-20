"""Username/password gate.

Credentials come from Streamlit secrets:

    [auth]
    username = "dinu"
    password = "..."

If no [auth] section exists (local use on your own machine), the gate is off.
"""
from __future__ import annotations

import hmac
import time

import streamlit as st

MAX_FAILS = 5
LOCK_SECONDS = 120


def _creds():
    try:
        a = st.secrets.get("auth")
    except Exception:
        return None
    if not a or not a.get("username") or not a.get("password"):
        return None
    return str(a["username"]), str(a["password"])


def enabled() -> bool:
    return _creds() is not None


def require_login() -> None:
    creds = _creds()
    if creds is None or st.session_state.get("authed"):
        return
    st.markdown("## QFin Lab")
    st.caption("Private learning app. Sign in to continue.")
    locked_until = st.session_state.get("lock_until", 0)
    if time.time() < locked_until:
        st.error(f"Too many failed attempts. Try again in {int(locked_until - time.time())} s.")
        st.stop()
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        ok = st.form_submit_button("Sign in", type="primary")
    if ok:
        good = hmac.compare_digest(u.strip().encode(), creds[0].encode()) & hmac.compare_digest(p.encode(), creds[1].encode())
        if good:
            st.session_state["authed"] = True
            st.session_state.pop("fails", None)
            st.rerun()
        fails = st.session_state.get("fails", 0) + 1
        st.session_state["fails"] = fails
        if fails >= MAX_FAILS:
            st.session_state["lock_until"] = time.time() + LOCK_SECONDS
            st.session_state["fails"] = 0
        st.error("Wrong username or password.")
    st.stop()


def logout_button() -> None:
    if enabled() and st.session_state.get("authed"):
        if st.sidebar.button("Sign out"):
            st.session_state.clear()
            st.rerun()
