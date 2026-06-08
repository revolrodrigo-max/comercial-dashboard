import pandas as pd
import streamlit as st
from pathlib import Path

DATA_DIR = Path(__file__).parent
TRIAGE_CACHE = DATA_DIR / "triage_cache.csv"
CLOSER_CACHE = DATA_DIR / "closer_cache.csv"


def _load_from_file(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path, dtype=str)
    return pd.DataFrame()


def render_upload_panel():
    """
    Sidebar panel for uploading CSVs exported from Google Sheets.
    Saves them locally so the app reloads fast on next run.
    """
    with st.sidebar.expander("📂 Actualizar datos", expanded=not TRIAGE_CACHE.exists()):
        st.caption(
            "Exportá cada planilla desde Google Sheets: "
            "**Archivo → Descargar → CSV** y subí el archivo acá."
        )

        uploaded_triage = st.file_uploader(
            "Planilla de Triage (.csv)", type="csv", key="up_triage"
        )
        if uploaded_triage:
            df = pd.read_csv(uploaded_triage, dtype=str)
            df.to_csv(TRIAGE_CACHE, index=False)
            st.success(f"Triage cargado: {len(df)} filas")
            st.cache_data.clear()

        uploaded_closer = st.file_uploader(
            "Tracker de Closers (.csv)", type="csv", key="up_closer"
        )
        if uploaded_closer:
            df = pd.read_csv(uploaded_closer, dtype=str)
            df.to_csv(CLOSER_CACHE, index=False)
            st.success(f"Tracker cargado: {len(df)} filas")
            st.cache_data.clear()

        if TRIAGE_CACHE.exists():
            import os, datetime
            mtime = os.path.getmtime(TRIAGE_CACHE)
            last = datetime.datetime.fromtimestamp(mtime).strftime("%d/%m %H:%M")
            st.caption(f"Última actualización triage: {last}")
        if CLOSER_CACHE.exists():
            import os, datetime
            mtime = os.path.getmtime(CLOSER_CACHE)
            last = datetime.datetime.fromtimestamp(mtime).strftime("%d/%m %H:%M")
            st.caption(f"Última actualización tracker: {last}")


@st.cache_data(show_spinner="Cargando triage…")
def load_triage_raw() -> pd.DataFrame:
    df = _load_from_file(TRIAGE_CACHE)
    if df.empty:
        st.warning("Sin datos de triage. Subí el CSV en el panel lateral.", icon="📂")
    return df


@st.cache_data(show_spinner="Cargando tracker de closers…")
def load_closer_raw() -> pd.DataFrame:
    df = _load_from_file(CLOSER_CACHE)
    if df.empty:
        st.warning("Sin datos del tracker. Subí el CSV en el panel lateral.", icon="📂")
    return df
