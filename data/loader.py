import pandas as pd
import streamlit as st
from pathlib import Path
from config import TRIAGE_SHEET_ID, CLOSER_SHEET_ID

CACHE_TTL = 300  # seconds
DATA_DIR = Path(__file__).parent
TRIAGE_CACHE = DATA_DIR / "triage_cache.csv"
CLOSER_CACHE = DATA_DIR / "closer_cache.csv"


def _sheet_url(sheet_id: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"


def _load_from_url(url: str) -> pd.DataFrame:
    return pd.read_csv(url, dtype=str)


def _load_from_file(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path, dtype=str)
    return pd.DataFrame()


def render_upload_panel():
    """Fallback upload panel — only shown if the live URL fails."""
    with st.sidebar.expander("📂 Cargar datos manualmente", expanded=False):
        st.caption(
            "Usá esto solo si la carga automática falla. "
            "Exportá desde Google Sheets: **Archivo → Descargar → CSV**."
        )
        uploaded_triage = st.file_uploader("Planilla de Triage (.csv)", type="csv", key="up_triage")
        if uploaded_triage:
            df = pd.read_csv(uploaded_triage, dtype=str)
            df.to_csv(TRIAGE_CACHE, index=False)
            st.success(f"Triage cargado: {len(df)} filas")
            st.cache_data.clear()

        uploaded_closer = st.file_uploader("Tracker de Ventas (.csv)", type="csv", key="up_closer")
        if uploaded_closer:
            df = pd.read_csv(uploaded_closer, dtype=str)
            df.to_csv(CLOSER_CACHE, index=False)
            st.success(f"Tracker cargado: {len(df)} filas")
            st.cache_data.clear()


@st.cache_data(ttl=CACHE_TTL, show_spinner="Actualizando triage…")
def load_triage_raw() -> pd.DataFrame:
    try:
        df = _load_from_url(_sheet_url(TRIAGE_SHEET_ID))
        df.to_csv(TRIAGE_CACHE, index=False)  # keep local backup
        return df
    except Exception as e:
        st.warning(f"No se pudo cargar triage en vivo ({e}). Usando última copia local.")
        return _load_from_file(TRIAGE_CACHE)


@st.cache_data(ttl=CACHE_TTL, show_spinner="Actualizando tracker de ventas…")
def load_closer_raw() -> pd.DataFrame:
    try:
        df = _load_from_url(_sheet_url(CLOSER_SHEET_ID))
        df.to_csv(CLOSER_CACHE, index=False)  # keep local backup
        return df
    except Exception as e:
        st.warning(f"No se pudo cargar el tracker en vivo ({e}). Usando última copia local.")
        return _load_from_file(CLOSER_CACHE)
