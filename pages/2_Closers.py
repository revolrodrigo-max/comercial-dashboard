import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from data.loader import load_triage_raw, load_closer_raw
from processing.triage import process_triage
from processing.closer import process_closer
from config import CLOSER_COLORS

st.set_page_config(page_title="Closers", page_icon="👥", layout="wide")
st.title("👥 Métricas por Closer")

closer = process_closer(load_closer_raw())

if closer.empty:
    st.warning("Sin datos de closers.")
    st.stop()

# ── Filters ───────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    all_months = sorted(closer["mes"].dropna().unique(), reverse=True)
    sel_month = st.selectbox("Mes", ["Todos"] + list(all_months))
with col2:
    granularity = st.selectbox("Tendencia por", ["Semana", "Mes"])

if sel_month != "Todos":
    closer = closer[closer["mes"] == sel_month]

# ── Per-closer summary ────────────────────────────────────────────────────────
if "closer" in closer.columns:
    grp = closer.groupby("closer").agg(
        leads=("lead", "count"),
        asistieron=("asistio", "sum"),
        calificaron=("califico", "sum"),
        compraron=("compro", "sum"),
        revenue=("revenue", "sum"),
        cash=("cash_collected", "sum"),
    ).reset_index()

    grp["show_rate"] = grp["asistieron"] / grp["leads"]
    grp["calif_rate"] = grp.apply(
        lambda r: r["calificaron"] / r["asistieron"] if r["asistieron"] else 0, axis=1
    )
    grp["close_rate"] = grp.apply(
        lambda r: r["compraron"] / r["calificaron"] if r["calificaron"] else 0, axis=1
    )
    grp["ticket_prom"] = grp.apply(
        lambda r: r["revenue"] / r["compraron"] if r["compraron"] else 0, axis=1
    )

    # ── KPI cards per closer ──────────────────────────────────────────────────
    cols = st.columns(len(grp))
    for i, row in grp.iterrows():
        color = CLOSER_COLORS.get(row["closer"], "#888888")
        with cols[i]:
            st.markdown(
                f"<div style='border-left:4px solid {color};padding:8px 12px'>"
                f"<b style='font-size:1.1em'>{row['closer']}</b><br>"
                f"Leads: {row['leads']}<br>"
                f"Show: {row['show_rate']:.0%} &nbsp;|&nbsp; Cierre: {row['close_rate']:.0%}<br>"
                f"Revenue: ${row['revenue']:,.0f}<br>"
                f"Cash: ${row['cash']:,.0f}<br>"
                f"Ticket prom: ${row['ticket_prom']:,.0f}"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Comparison bar charts ─────────────────────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Tasa de cierre por closer")
        colors = [CLOSER_COLORS.get(c, "#CCCCCC") for c in grp["closer"]]
        fig = go.Figure(go.Bar(
            x=grp["closer"], y=grp["close_rate"],
            marker_color=colors,
            text=grp["close_rate"].apply(lambda v: f"{v:.0%}"),
            textposition="outside",
        ))
        fig.update_layout(yaxis_tickformat=".0%", height=300,
                          margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Revenue vs. Cash Collected")
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            name="Revenue", x=grp["closer"], y=grp["revenue"],
            marker_color=[CLOSER_COLORS.get(c, "#CCCCCC") for c in grp["closer"]],
        ))
        fig2.add_trace(go.Bar(
            name="Cash Collected", x=grp["closer"], y=grp["cash"],
            marker_color=["#27AE60" for _ in grp["closer"]],
            opacity=0.7,
        ))
        fig2.update_layout(barmode="group", height=300,
                           margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── Trends over time ──────────────────────────────────────────────────────
    st.subheader(f"Tendencia de revenue por {granularity.lower()}")
    group_col = "semana" if granularity == "Semana" else "mes"

    if group_col in closer.columns:
        trend = (
            closer[closer["revenue"] > 0]
            .groupby([group_col, "closer"])["revenue"]
            .sum()
            .reset_index()
            .sort_values(group_col)
        )
        fig_trend = px.line(
            trend, x=group_col, y="revenue", color="closer",
            color_discrete_map=CLOSER_COLORS,
            markers=True,
            labels={group_col: granularity, "revenue": "Revenue USD"},
        )
        fig_trend.update_layout(height=350, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig_trend, use_container_width=True)

    st.divider()

    # ── Medios de pago por closer ─────────────────────────────────────────────
    st.subheader("Medios de pago por closer")
    if "medio_pago" in closer.columns:
        pay_df = (
            closer[closer["medio_pago"].notna() & (closer["medio_pago"].str.strip() != "")]
            .groupby(["closer", "medio_pago"])
            .size()
            .reset_index(name="cantidad")
        )
        fig_pay = px.bar(
            pay_df, x="closer", y="cantidad", color="medio_pago",
            barmode="stack",
            labels={"cantidad": "Operaciones", "medio_pago": "Medio de pago"},
        )
        fig_pay.update_layout(height=320, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig_pay, use_container_width=True)

    st.divider()

    # ── Full detail table ─────────────────────────────────────────────────────
    st.subheader("Detalle por closer")
    sel_c = st.selectbox("Ver detalle de", grp["closer"].tolist())
    sub = closer[closer["closer"] == sel_c].sort_values("fecha", ascending=False)
    show_cols = ["fecha", "lead", "asistencia", "califica", "compra",
                 "tipo_pago", "revenue", "cash_collected", "medio_pago",
                 "estado_seguimiento", "notas"]
    avail = [col for col in show_cols if col in sub.columns]
    st.dataframe(sub[avail], use_container_width=True, hide_index=True)
