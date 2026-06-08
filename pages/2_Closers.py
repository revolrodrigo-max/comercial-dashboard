import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from data.loader import load_closer_raw
from processing.closer import process_closer
from config import CLOSER_COLORS, BRAND_GREEN, BRAND_WHITE, BRAND_GREY, BRAND_BLACK
from ui import inject_css, page_header
from auth import require_auth

st.set_page_config(page_title="Closers", page_icon="👥", layout="wide")
inject_css()
require_auth()

_dark = dict(paper_bgcolor="#141414", plot_bgcolor="#141414",
             font=dict(color=BRAND_WHITE, family="Inter"), margin=dict(l=10, r=10, t=20, b=10))

page_header("Métricas por Closer", "Rendimiento individual y comparativo del equipo")

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

    grp["show_rate"]   = grp["asistieron"] / grp["leads"]
    grp["calif_rate"]  = grp.apply(lambda r: r["calificaron"] / r["asistieron"] if r["asistieron"] else 0, axis=1)
    grp["close_rate"]  = grp.apply(lambda r: r["compraron"] / r["calificaron"] if r["calificaron"] else 0, axis=1)
    grp["ticket_prom"] = grp.apply(lambda r: r["revenue"] / r["compraron"] if r["compraron"] else 0, axis=1)

    cols = st.columns(len(grp))
    for i, row in grp.iterrows():
        color = CLOSER_COLORS.get(row["closer"], BRAND_GREY)
        with cols[i]:
            st.markdown(
                f"<div style='border:1px solid {color};border-radius:8px;padding:16px;"
                f"background:#111111'>"
                f"<div style='color:{color};font-size:1.1em;font-weight:700'>{row['closer']}</div>"
                f"<div style='color:#6B6969;font-size:.75rem;margin-bottom:8px'>{int(row['leads'])} leads</div>"
                f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:4px'>"
                f"<span style='color:#FFFFFF'>Show</span><span style='color:{color}'>{row['show_rate']:.0%}</span>"
                f"<span style='color:#FFFFFF'>Cierre</span><span style='color:{color}'>{row['close_rate']:.0%}</span>"
                f"<span style='color:#FFFFFF'>Revenue</span><span style='color:{color}'>${row['revenue']:,.0f}</span>"
                f"<span style='color:#FFFFFF'>Cash</span><span style='color:{color}'>${row['cash']:,.0f}</span>"
                f"<span style='color:#FFFFFF'>Ticket</span><span style='color:{color}'>${row['ticket_prom']:,.0f}</span>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Comparison charts ─────────────────────────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Tasa de cierre")
        bar_colors = [CLOSER_COLORS.get(c, BRAND_GREY) for c in grp["closer"]]
        fig = go.Figure(go.Bar(
            x=grp["closer"], y=grp["close_rate"],
            marker_color=bar_colors,
            marker_line_color=BRAND_BLACK, marker_line_width=1,
            text=grp["close_rate"].apply(lambda v: f"{v:.0%}"),
            textposition="outside",
            textfont=dict(color=BRAND_WHITE),
        ))
        fig.update_layout(**_dark, height=300, yaxis_tickformat=".0%",
                           yaxis=dict(gridcolor="#3A3A3A"))
        st.plotly_chart(fig, width='stretch')

    with col_b:
        st.subheader("Revenue vs. Cash Collected")
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            name="Revenue", x=grp["closer"], y=grp["revenue"],
            marker_color=BRAND_GREEN, marker_line_color=BRAND_BLACK, marker_line_width=1,
        ))
        fig2.add_trace(go.Bar(
            name="Cash Collected", x=grp["closer"], y=grp["cash"],
            marker_color=BRAND_GREY, marker_line_color=BRAND_BLACK, marker_line_width=1,
        ))
        fig2.update_layout(**_dark, barmode="group", height=300,
                            legend=dict(bgcolor="#111111"),
                            yaxis=dict(gridcolor="#3A3A3A"))
        st.plotly_chart(fig2, width='stretch')

    st.divider()

    # ── Trend ─────────────────────────────────────────────────────────────────
    st.subheader(f"Tendencia de revenue por {granularity.lower()}")
    group_col = "semana" if granularity == "Semana" else "mes"
    if group_col in closer.columns:
        trend = (
            closer[closer["revenue"] > 0]
            .groupby([group_col, "closer"])["revenue"]
            .sum().reset_index().sort_values(group_col)
        )
        fig_trend = px.line(
            trend, x=group_col, y="revenue", color="closer",
            color_discrete_map=CLOSER_COLORS, markers=True,
            labels={group_col: granularity, "revenue": "Revenue USD"},
        )
        fig_trend.update_layout(
            **_dark, height=350,
            legend=dict(bgcolor="#111111"),
            xaxis=dict(gridcolor="#3A3A3A"),
            yaxis=dict(gridcolor="#3A3A3A"),
        )
        st.plotly_chart(fig_trend, width='stretch')

    st.divider()

    # ── Detail table ──────────────────────────────────────────────────────────
    st.subheader("Detalle por closer")
    sel_c = st.selectbox("Ver detalle de", grp["closer"].tolist())
    sub = closer[closer["closer"] == sel_c].sort_values("fecha", ascending=False)
    show_cols = ["fecha", "lead", "asistencia", "califica", "compra",
                 "revenue", "cash_collected", "medio_pago", "estado_seguimiento", "notas"]
    avail = [col for col in show_cols if col in sub.columns]
    st.dataframe(sub[avail], width='stretch', hide_index=True)
