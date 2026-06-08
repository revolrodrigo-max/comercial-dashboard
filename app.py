import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from data.loader import load_triage_raw, load_closer_raw, render_upload_panel
from processing.triage import process_triage
from processing.closer import process_closer
from processing.funnel import kpis, funnel_counts, merge_funnel
from config import CLOSER_COLORS

st.set_page_config(
    page_title="Dashboard Comercial",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.title("Dashboard Comercial")
st.sidebar.caption("Triage + Closers — datos en vivo")

render_upload_panel()

if st.sidebar.button("🔄 Recargar datos", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# ── Load & process ────────────────────────────────────────────────────────────
triage_raw = load_triage_raw()
closer_raw = load_closer_raw()

triage = process_triage(triage_raw)
closer = process_closer(closer_raw)
funnel_df = merge_funnel(triage, closer)

# ── Sidebar filters ───────────────────────────────────────────────────────────
all_months = sorted(closer["mes"].dropna().unique(), reverse=True) if not closer.empty else []
sel_month = st.sidebar.selectbox("Mes", ["Todos"] + all_months)

all_closers = sorted(closer["closer"].dropna().unique()) if not closer.empty else []
sel_closer = st.sidebar.multiselect("Closer", all_closers, default=all_closers)

def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if sel_month != "Todos" and "mes" in df.columns:
        df = df[df["mes"] == sel_month]
    if sel_closer and "closer" in df.columns:
        df = df[df["closer"].isin(sel_closer)]
    return df

c_filtered = apply_filters(closer)
t_filtered = triage if triage.empty else (
    triage[triage["mes"] == sel_month] if sel_month != "Todos" else triage
)

# ── KPIs ──────────────────────────────────────────────────────────────────────
st.title("📊 Resumen Comercial")
metrics = kpis(c_filtered)

if not metrics:
    st.warning("Sin datos. Verificá que las planillas estén compartidas públicamente.")
    st.stop()

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Leads agendados", metrics["total_leads"])
col2.metric("Asistieron", metrics["asistieron"], f"{metrics['show_rate']:.0%} show rate")
col3.metric("Calificaron", metrics["calificaron"], f"{metrics['calif_rate']:.0%}")
col4.metric("Compraron", metrics["compraron"], f"{metrics['close_rate']:.0%} cierre")
col5.metric("Revenue", f"${metrics['revenue']:,.0f}")
col6.metric("Cash Collected", f"${metrics['cash_collected']:,.0f}")

st.divider()

# ── Funnel + Revenue by closer ────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Funnel de conversión")
    fc = funnel_counts(c_filtered, source="closer")
    fig_funnel = go.Figure(go.Funnel(
        y=fc["etapa"],
        x=fc["cantidad"],
        textinfo="value+percent initial",
        marker={"color": ["#4C9BE8", "#6FCF97", "#F2C94C", "#27AE60"]},
    ))
    fig_funnel.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=320)
    st.plotly_chart(fig_funnel, use_container_width=True)

with col_right:
    st.subheader("Revenue por closer")
    if not c_filtered.empty and "closer" in c_filtered.columns:
        rev_by_closer = (
            c_filtered.groupby("closer")["revenue"]
            .sum()
            .reset_index()
            .sort_values("revenue", ascending=True)
        )
        colors = [CLOSER_COLORS.get(c, "#CCCCCC") for c in rev_by_closer["closer"]]
        fig_rev = go.Figure(go.Bar(
            y=rev_by_closer["closer"],
            x=rev_by_closer["revenue"],
            orientation="h",
            marker_color=colors,
            text=rev_by_closer["revenue"].apply(lambda v: f"${v:,.0f}"),
            textposition="outside",
        ))
        fig_rev.update_layout(margin=dict(l=0, r=60, t=10, b=0), height=320,
                               xaxis_title="Revenue USD")
        st.plotly_chart(fig_rev, use_container_width=True)

st.divider()

# ── Revenue semanal ───────────────────────────────────────────────────────────
st.subheader("Revenue semanal")
if not c_filtered.empty and "semana" in c_filtered.columns:
    weekly = (
        c_filtered[c_filtered["revenue"] > 0]
        .groupby(["semana", "closer"])["revenue"]
        .sum()
        .reset_index()
        .sort_values("semana")
    )
    fig_weekly = px.bar(
        weekly, x="semana", y="revenue", color="closer",
        color_discrete_map=CLOSER_COLORS,
        labels={"semana": "Semana", "revenue": "Revenue USD", "closer": "Closer"},
    )
    fig_weekly.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=300)
    st.plotly_chart(fig_weekly, use_container_width=True)

st.divider()

# ── Recent leads table ────────────────────────────────────────────────────────
st.subheader("Leads recientes")
if not c_filtered.empty:
    show_cols = ["fecha", "lead", "closer", "asistencia", "califica",
                 "compra", "tipo_pago", "revenue", "cash_collected", "estado_seguimiento"]
    available = [col for col in show_cols if col in c_filtered.columns]
    recent = c_filtered.sort_values("fecha", ascending=False).head(50)[available]
    st.dataframe(recent, use_container_width=True, hide_index=True)
