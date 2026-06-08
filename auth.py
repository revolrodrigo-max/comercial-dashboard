"""Simple password gate shared across all pages.

The password is read from Streamlit secrets (`st.secrets["app_password"]`).
Locally that comes from .streamlit/secrets.toml (gitignored); on Streamlit
Cloud you set it in the app's Secrets panel. If no secret is configured,
a default is used so the app still runs on a fresh machine.
"""

import streamlit as st

_DEFAULT_PASSWORD = "comercial2026"


def _expected_password() -> str:
    try:
        return st.secrets["app_password"]
    except Exception:
        return _DEFAULT_PASSWORD


def require_auth():
    """Block the page until the correct password is entered."""
    if st.session_state.get("auth_ok"):
        return

    # Center the login form
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown(
            "<div style='text-align:center;padding:40px 0 10px'>"
            "<span style='font-size:2rem;font-weight:800;color:#C7FF00'>⚡ COMERCIAL</span>"
            "<p style='color:#8A8A8A;margin-top:4px'>Acceso restringido</p></div>",
            unsafe_allow_html=True,
        )
        pwd = st.text_input("Contraseña", type="password", key="_pwd_input",
                            label_visibility="collapsed", placeholder="Contraseña")
        if st.button("Ingresar", width="stretch"):
            if pwd == _expected_password():
                st.session_state["auth_ok"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        st.caption("Pedile la clave al administrador del dashboard.")

    st.stop()
