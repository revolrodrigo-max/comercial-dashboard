import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from data.loader import load_triage_raw, load_closer_raw
from processing.triage import process_triage
from processing.closer import process_closer
from processing.funnel import funnel_counts
from config import CLOSER_COLORS, PAYMENT_COLORS

st.set_page_config(page_title="Pipeline", page_icon="🔄", layout="wide")
st.title("🔄 Pipeline Interactivo")

triage = process_triage(load_triage_raw())
closer = process_closer(load_closer_raw())

# ── Filters ───────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    all_months = sorted(closer["mes"].dropna().unique(), reverse=True) if not closer.empty else []
    sel_month = st.selectbox("Mes", ["Todos"] + list(all_months))

with col2:
    all_closers = sorted(closer["closer"].dropna().unique()) if not closer.empty else []
    sel_closer = st.multiselect("Closer", all_closers, default=all_closers)

with col3:
    etapa_view = st.selectbox(
        "Vista de pipeline",
        ["Todos los leads", "Solo activos (sin resultado)", "Compraron", "No compraron (calificaron)"]
    )

def apply_filters(df):
    if df.empty:
        return df
    if sel_month != "Todos":
        df = df[df["mes"] == sel_month]
    if sel_closer:
        df = df[df["closer"].isin(sel_closer)]
    return df

c = apply_filters(closer)

if etapa_view == "Compraron":
    c = c[c["compro"] == True]
elif etapa_view == "No compraron (calificaron)":
    c = c[(c["califico"] == True) & (c["compro"] == False)]
elif etapa_view == "Solo activos (sin resultado)":
    c = c[c["compra"].isna() | (c["compra"].str.strip() == "")]

st.caption(f"{len(c)} leads en esta vista")

# ── Funnel principal ──────────────────────────────────────────────────────────
st.subheader("Embudo de conversión")
fc = funnel_counts(c, source="closer")

col_f, col_rates = st.columns([2, 1])

with col_f:
    fig = go.Figure(go.Funnel(
        y=fc["etapa"],
        x=fc["cantidad"],
        textinfo="value+percent initial+percent previous",
        marker={
            "color": ["#4C9BE8", "#6FCF97", "#F2C94C", "#27AE60"],
            "line": {"width": 2, "color": "white"},
        },
    ))
    fig.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

with col_rates:
    st.markdown("### Tasas de conversión")
    vals = fc["cantidad"].tolist()
    if len(vals) == 4 and vals[0] > 0:
        st.metric("Show rate", f"{vals[1]/vals[0]:.1%}", help="Asistieron / Agendados")
        st.metric("Calificación", f"{vals[2]/vals[1]:.1%}" if vals[1] else "—", help="Calificaron / Asistieron")
        st.metric("Cierre", f"{vals[3]/vals[2]:.1%}" if vals[2] else "—", help="Compraron / Calificaron")
        st.metric("Conversión total", f"{vals[3]/vals[0]:.1%}", help="Compraron / Agendados")

st.divider()

# ── Por closer ────────────────────────────────────────────────────────────────
st.subheader("Funnel por closer")
if not c.empty and "closer" in c.columns:
    closers_list = c["closer"].dropna().unique()
    cols = st.columns(min(len(closers_list), 4))

    for i, closer_name in enumerate(closers_list):
        sub = c[c["closer"] == closer_name]
        fc_sub = funnel_counts(sub, source="closer")
        color = CLOSER_COLORS.get(closer_name, "#AAAAAA")

        with cols[i % len(cols)]:
            st.markdown(f"**{closer_name}** — {len(sub)} leads")
            vals = fc_sub["cantidad"].tolist()
            if vals[0] > 0:
                close_r = vals[3] / vals[2] if vals[2] else 0
                show_r = vals[1] / vals[0]
                st.progress(show_r, text=f"Show {show_r:.0%}")
                st.progress(close_r, text=f"Cierre {close_r:.0%}")
                rev = sub["revenue"].sum()
                st.caption(f"Revenue: ${rev:,.0f}")

st.divider()

# ── Tipos de pago ─────────────────────────────────────────────────────────────
col_pay, col_cancel = st.columns(2)

with col_pay:
    st.subheader("Distribución de pagos")
    if not c.empty and "tipo_pago" in c.columns:
        pay = c[c["tipo_pago"].notna() & (c["tipo_pago"].str.strip() != "")]
        pay_counts = pay["tipo_pago"].value_counts().reset_index()
        pay_counts.columns = ["tipo", "cantidad"]
        colors = [PAYMENT_COLORS.get(t, "#CCCCCC") for t in pay_counts["tipo"]]
        fig_pay = go.Figure(go.Pie(
            labels=pay_counts["tipo"],
            values=pay_counts["cantidad"],
            marker_colors=colors,
            hole=0.4,
        ))
        fig_pay.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_pay, use_container_width=True)

with col_cancel:
    st.subheader("Motivos de cancelación / no-show")
    if not c.empty and "motivo_cancelacion" in c.columns:
        cancel = c[c["motivo_cancelacion"].notna() & (c["motivo_cancelacion"].str.strip() != "")]
        if not cancel.empty:
            mc = cancel["motivo_cancelacion"].value_counts().reset_index()
            mc.columns = ["motivo", "cantidad"]
            fig_cancel = px.bar(mc, x="cantidad", y="motivo", orientation="h",
                                color_discrete_sequence=["#EB5757"])
            fig_cancel.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0),
                                     yaxis_title="")
            st.plotly_chart(fig_cancel, use_container_width=True)
        else:
            st.info("Sin cancelaciones en este período.")

st.divider()

# ── Leads por etapa (tabla interactiva) ───────────────────────────────────────
st.subheader("Leads por etapa del pipeline")

tab_ag, tab_as, tab_cal, tab_comp, tab_nocomp = st.tabs(
    ["Agendados", "Asistieron", "Calificaron", "Compraron", "Calificaron pero no compraron"]
)

display_cols = ["fecha", "lead", "closer", "asistencia", "califica", "compra",
                "tipo_pago", "revenue", "cash_collected", "notas", "estado_seguimiento"]
avail = [col for col in display_cols if col in c.columns]

def show_table(df):
    if df.empty:
        st.info("Sin registros.")
    else:
        st.dataframe(df[avail].sort_values("fecha", ascending=False),
                     use_container_width=True, hide_index=True)

with tab_ag:
    show_table(c)
with tab_as:
    show_table(c[c["asistio"] == True])
with tab_cal:
    show_table(c[c["califico"] == True])
with tab_comp:
    show_table(c[c["compro"] == True])
with tab_nocomp:
    show_table(c[(c["califico"] == True) & (c["compro"] == False)])
