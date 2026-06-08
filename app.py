import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from data.loader import load_triage_raw, load_closer_raw
from processing.triage import process_triage
from processing.closer import process_closer
from processing.funnel import kpis, funnel_counts, merge_funnel
from config import CLOSER_COLORS, BRAND_GREEN, BRAND_WHITE, BRAND_GREY, BRAND_BLACK
from ui import inject_css, plotly_theme, page_header, section, SURFACE, MUTED, BORDER

st.set_page_config(page_title="Dashboard Comercial", page_icon="⚡",
                   layout="wide", initial_sidebar_state="expanded")
inject_css()

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown(
    f"<div style='padding:6px 0 14px'>"
    f"<span style='font-size:1.5rem;font-weight:800;color:{BRAND_GREEN};letter-spacing:-.02em'>⚡ COMERCIAL</span>"
    f"<div style='color:{MUTED};font-size:.78rem;margin-top:2px'>Inteligencia de ventas en vivo</div></div>",
    unsafe_allow_html=True,
)

if st.sidebar.button("🔄 Recargar datos", width='stretch'):
    st.cache_data.clear()
    st.rerun()

# ── Load ──────────────────────────────────────────────────────────────────────
triage   = process_triage(load_triage_raw())
closer   = process_closer(load_closer_raw())
funnel_df = merge_funnel(triage, closer)

if closer.empty:
    st.warning("Sin datos. Verificá que las planillas sigan compartidas como públicas.")
    st.stop()

# ── Filters ───────────────────────────────────────────────────────────────────
all_months  = sorted(closer["mes"].dropna().unique(), reverse=True)
sel_month   = st.sidebar.selectbox("Período", ["Todos"] + all_months)
all_closers = sorted(closer["closer"].dropna().unique())
sel_closer  = st.sidebar.multiselect("Closer", all_closers, default=all_closers)

st.sidebar.markdown(
    f"<div style='margin-top:18px;padding-top:14px;border-top:1px solid {BORDER};"
    f"color:{MUTED};font-size:.74rem;line-height:1.6'>"
    f"📊 {len(closer):,} leads · {len(all_months)} meses<br>"
    f"👥 {len(all_closers)} closers activos</div>",
    unsafe_allow_html=True,
)


def apply_filters(df):
    if df.empty:
        return df
    if sel_month != "Todos" and "mes" in df.columns:
        df = df[df["mes"] == sel_month]
    if sel_closer and "closer" in df.columns:
        df = df[df["closer"].isin(sel_closer)]
    return df


c = apply_filters(closer)
metrics = kpis(c)

# Month-over-month deltas
prev_metrics = {}
if sel_month != "Todos" and sel_month in all_months:
    idx = all_months.index(sel_month)
    if idx + 1 < len(all_months):
        prev = closer[closer["mes"] == all_months[idx + 1]]
        if sel_closer:
            prev = prev[prev["closer"].isin(sel_closer)]
        prev_metrics = kpis(prev)


def delta(key, fmt="num"):
    if not prev_metrics or not prev_metrics.get(key):
        return None
    cur, prv = metrics.get(key, 0), prev_metrics.get(key, 0)
    if prv == 0:
        return None
    pct = (cur - prv) / prv
    return f"{pct:+.0%} vs mes ant."


# ── Header + KPIs ─────────────────────────────────────────────────────────────
periodo = "Histórico completo" if sel_month == "Todos" else sel_month
page_header("Resumen Comercial", f"{periodo} · {len(c):,} leads en vista")

if not metrics:
    st.info("Sin datos para los filtros seleccionados.")
    st.stop()

r1 = st.columns(3)
r1[0].metric("Revenue",         f"${metrics['revenue']:,.0f}",        delta("revenue"))
r1[1].metric("Cash Collected",  f"${metrics['cash_collected']:,.0f}", delta("cash_collected"))
r1[2].metric("Ventas cerradas", f"{metrics['compraron']}",            delta("compraron"))

r2 = st.columns(4)
r2[0].metric("Leads agendados", f"{metrics['total_leads']}",          delta("total_leads"))
r2[1].metric("Show rate",       f"{metrics['show_rate']:.0%}")
r2[2].metric("Tasa de cierre",  f"{metrics['close_rate']:.0%}")
r2[3].metric("Ticket promedio", f"${metrics['ticket_promedio']:,.0f}")

st.divider()

# ── Funnel + Revenue por closer ───────────────────────────────────────────────
col_l, col_r = st.columns([5, 6])

with col_l:
    section("Embudo de conversión")
    fc = funnel_counts(c, source="closer")
    fig = go.Figure(go.Funnel(
        y=fc["etapa"], x=fc["cantidad"],
        textinfo="value+percent initial",
        textfont=dict(color=BRAND_BLACK, size=13, family="Inter"),
        marker={"color": ["#2A2A2A", "#5A5A5A", "#9ECC00", BRAND_GREEN],
                "line": {"width": 0}},
        connector={"line": {"color": BORDER, "width": 1}},
    ))
    fig.update_layout(**plotly_theme(height=340, legend=False))
    st.plotly_chart(fig, width='stretch')

with col_r:
    section("Revenue por closer")
    rev = (c.groupby("closer")["revenue"].sum().reset_index()
             .sort_values("revenue"))
    colors = [CLOSER_COLORS.get(x, BRAND_GREY) for x in rev["closer"]]
    fig2 = go.Figure(go.Bar(
        y=rev["closer"], x=rev["revenue"], orientation="h",
        marker=dict(color=colors),
        text=rev["revenue"].apply(lambda v: f"  ${v:,.0f}"),
        textposition="outside", textfont=dict(color=BRAND_WHITE),
        cliponaxis=False,
    ))
    fig2.update_layout(**plotly_theme(height=340, legend=False))
    st.plotly_chart(fig2, width='stretch')

st.divider()

# ── Tendencia mensual de revenue ──────────────────────────────────────────────
section("Evolución mensual")
col_a, col_b = st.columns([7, 5])

with col_a:
    monthly = (closer if sel_month == "Todos" else closer)  # always show full trend
    if sel_closer:
        monthly = monthly[monthly["closer"].isin(sel_closer)]
    m_rev = monthly.groupby("mes").agg(
        revenue=("revenue", "sum"), ventas=("compro", "sum")
    ).reset_index().sort_values("mes")

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        x=m_rev["mes"], y=m_rev["revenue"], name="Revenue",
        marker_color=BRAND_GREEN, marker_line_width=0,
    ))
    fig3.add_trace(go.Scatter(
        x=m_rev["mes"], y=m_rev["ventas"] * (m_rev["revenue"].max() / max(m_rev["ventas"].max(), 1)),
        name="Ventas (esc.)", yaxis="y2", mode="lines+markers",
        line=dict(color=BRAND_WHITE, width=2), marker=dict(size=6),
    ))
    lay = plotly_theme(height=320)
    lay["yaxis2"] = dict(overlaying="y", side="right", showgrid=False, color=MUTED)
    fig3.update_layout(**lay)
    st.plotly_chart(fig3, width='stretch')

with col_b:
    # Share de revenue por closer (donut)
    share = monthly.groupby("closer")["revenue"].sum().reset_index()
    fig4 = go.Figure(go.Pie(
        labels=share["closer"], values=share["revenue"], hole=0.62,
        marker=dict(colors=[CLOSER_COLORS.get(x, BRAND_GREY) for x in share["closer"]],
                    line=dict(color=SURFACE, width=2)),
        textinfo="percent", textfont=dict(color=BRAND_BLACK, size=12),
    ))
    lay = plotly_theme(height=320, legend=True)
    fig4.update_layout(**lay,
                       annotations=[dict(text="Revenue<br>share", x=.5, y=.5,
                                         font=dict(color=MUTED, size=12), showarrow=False)])
    st.plotly_chart(fig4, width='stretch')

st.divider()

# ── Leads recientes ───────────────────────────────────────────────────────────
section("Actividad reciente")
cols_show = ["fecha", "lead", "closer", "asistencia", "califica", "compra",
             "revenue", "cash_collected", "medio_pago", "estado_seguimiento"]
avail = [x for x in cols_show if x in c.columns]
st.dataframe(
    c.sort_values("fecha", ascending=False).head(40)[avail],
    width='stretch', hide_index=True,
    column_config={
        "fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YY"),
        "revenue": st.column_config.NumberColumn("Revenue", format="$%d"),
        "cash_collected": st.column_config.NumberColumn("Cash", format="$%d"),
    },
)
