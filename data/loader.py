import pandas as pd
import streamlit as st
from config import TRIAGE_SHEET_ID, CLOSER_SHEET_ID, CACHE_TTL


def _csv_url(sheet_id: str, gid: int = 0) -> str:
    return (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        f"/export?format=csv&gid={gid}"
    )


@st.cache_data(ttl=CACHE_TTL, show_spinner="Actualizando datos de triage…")
def load_triage_raw() -> pd.DataFrame:
    try:
        return pd.read_csv(_csv_url(TRIAGE_SHEET_ID), dtype=str, header=0)
    except Exception as e:
        st.error(f"No se pudo cargar triage: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL, show_spinner="Actualizando tracker de closers…")
def load_closer_raw() -> pd.DataFrame:
    try:
        return pd.read_csv(_csv_url(CLOSER_SHEET_ID), dtype=str, header=0)
    except Exception as e:
        st.error(f"No se pudo cargar el tracker: {e}")
        return pd.DataFrame()
