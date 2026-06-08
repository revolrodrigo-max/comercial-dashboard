import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from data.loader import load_triage_raw, load_closer_raw
from processing.triage import process_triage
from processing.closer import process_closer
from processing.funnel import funnel_counts
from config import CLOSER_COLORS, PAYMENT_COLORS, BRAND_GREEN, BRAND_WHITE, BRAND_GREY, BRAND_BLACK
from ui import inject_css, page_header

st.set_page_config(page_title="Pipeline", page_icon="🔄", layout="wide")
inject_css()

_dark = dict(paper_bgcolor="#141414", plot_bgcolor="#141414",
             font=dict(color=BRAND_WHITE, family="Inter"), margin=dict(l=10, r=10, t=20, b=10))

page_header("Pipeline Interactivo", "Embudo de conversión por etapa y closer")

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
    etapa_view = st.selectbox("Vista", [
        "Todos los leads", "Solo activos (sin resultado)",
        "Compraron", "No compraron (calificaron)"
    ])


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
            "color": ["#3A3A3A", "#6B6969", "#9ECC00", BRAND_GREEN],
            "line": {"width": 1, "color": BRAND_BLACK},
        },
        connector={"line": {"color": "#3A3A3A", "width": 1}},
    ))
    fig.update_layout(**_dark, height=400)
    st.plotly_chart(fig, width='stretch')

with col_rates:
    st.markdown("### Tasas")
    vals = fc["cantidad"].tolist()
    if len(vals) == 4 and vals[0] > 0:
        st.metric("Show rate",        f"{vals[1]/vals[0]:.1%}" if vals[0] else "—")
        st.metric("Calificación",     f"{vals[2]/vals[1]:.1%}" if vals[1] else "—")
        st.metric("Cierre",           f"{vals[3]/vals[2]:.1%}" if vals[2] else "—")
        st.metric("Conversión total", f"{vals[3]/vals[0]:.1%}")

st.divider()

# ── Por closer ────────────────────────────────────────────────────────────────
st.subheader("Funnel por closer")
if not c.empty and "closer" in c.columns:
    closers_list = c["closer"].dropna().unique()
    cols = st.columns(min(len(closers_list), 4))
    for i, closer_name in enumerate(closers_list):
        sub = c[c["closer"] == closer_name]
        fc_sub = funnel_counts(sub, source="closer")
        color = CLOSER_COLORS.get(closer_name, BRAND_GREY)
        vals = fc_sub["cantidad"].tolist()
        with cols[i % len(cols)]:
            st.markdown(
                f"<div style='border-left:3px solid {color};padding:10px 14px;"
                f"background:#111111;border-radius:4px'>"
                f"<b style='color:{color}'>{closer_name}</b>"
                f"<span style='color:#6B6969;font-size:.8rem'> — {len(sub)} leads</span></div>",
                unsafe_allow_html=True,
            )
            if vals[0] > 0:
                show_r  = vals[1] / vals[0]
                close_r = vals[3] / vals[2] if vals[2] else 0
                st.progress(show_r,  text=f"Show {show_r:.0%}")
                st.progress(close_r, text=f"Cierre {close_r:.0%}")
                st.caption(f"Revenue: ${sub['revenue'].sum():,.0f}")

st.divider()

# ── Tipos de pago / cancelaciones ─────────────────────────────────────────────
col_pay, col_cancel = st.columns(2)

with col_pay:
    st.subheader("Distribución de pagos")
    if not c.empty and "medio_pago" in c.columns:
        pay = c[c["medio_pago"].notna() & (c["medio_pago"].str.strip() != "")]
        if not pay.empty:
            pay_counts = pay["medio_pago"].value_counts().reset_index()
            pay_counts.columns = ["tipo", "cantidad"]
            fig_pay = go.Figure(go.Pie(
                labels=pay_counts["tipo"],
                values=pay_counts["cantidad"],
                hole=0.5,
                marker=dict(
                    colors=[BRAND_GREEN, BRAND_WHITE, BRAND_GREY, "#3A3A3A"],
                    line=dict(color=BRAND_BLACK, width=2),
                ),
                textfont=dict(color=BRAND_BLACK),
            ))
            fig_pay.update_layout(**_dark, height=280)
            st.plotly_chart(fig_pay, width='stretch')

with col_cancel:
    st.subheader("Asistencia — distribución")
    if not c.empty and "asistencia" in c.columns:
        asist = c["asistencia"].dropna().str.strip().value_counts().reset_index()
        asist.columns = ["estado", "cantidad"]
        color_map = {"Asiste": BRAND_GREEN, "No asiste": "#3A3A3A",
                     "Reprograma": BRAND_GREY, "Cancela": "#6B6969"}
        fig_asist = px.bar(asist, x="cantidad", y="estado", orientation="h",
                           color="estado", color_discrete_map=color_map)
        fig_asist.update_layout(**_dark, height=280, showlegend=False,
                                 xaxis=dict(gridcolor="#3A3A3A"),
                                 yaxis=dict(title=""))
        st.plotly_chart(fig_asist, width='stretch')

st.divider()

# ── Tabs por etapa ────────────────────────────────────────────────────────────
st.subheader("Leads por etapa")
tab_ag, tab_as, tab_cal, tab_comp, tab_nocomp = st.tabs(
    ["Agendados", "Asistieron", "Calificaron", "Compraron", "Calificaron, no compraron"]
)
display_cols = ["fecha", "lead", "closer", "asistencia", "califica", "compra",
                "revenue", "cash_collected", "notas", "estado_seguimiento"]
avail = [col for col in display_cols if col in c.columns]


def show_table(df):
    if df.empty:
        st.info("Sin registros.")
    else:
        st.dataframe(df[avail].sort_values("fecha", ascending=False),
                     width='stretch', hide_index=True)


with tab_ag:   show_table(c)
with tab_as:   show_table(c[c["asistio"] == True])
with tab_cal:  show_table(c[c["califico"] == True])
with tab_comp: show_table(c[c["compro"] == True])
with tab_nocomp: show_table(c[(c["califico"] == True) & (c["compro"] == False)])
