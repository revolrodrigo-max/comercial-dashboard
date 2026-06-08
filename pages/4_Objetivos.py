import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import json
import datetime
import calendar
from pathlib import Path

from data.loader import load_closer_raw
from processing.closer import process_closer
from processing.funnel import kpis
from config import BRAND_GREEN, BRAND_WHITE, BRAND_GREY, BRAND_BLACK
from ui import inject_css, page_header

st.set_page_config(page_title="Objetivos", page_icon="🎯", layout="wide")
inject_css()

_dark = dict(paper_bgcolor="#141414", plot_bgcolor="#141414",
             font=dict(color=BRAND_WHITE, family="Inter"), margin=dict(l=30, r=30, t=50, b=10))

page_header("Objetivos Mensuales", "Carga de metas y seguimiento de avance en tiempo real")

OBJETIVOS_PATH = Path(__file__).parent.parent / "data" / "objetivos.json"


def load_objetivos():
    if OBJETIVOS_PATH.exists():
        with open(OBJETIVOS_PATH) as f:
            return json.load(f)
    return {}


def save_objetivos(data):
    with open(OBJETIVOS_PATH, "w") as f:
        json.dump(data, f, indent=2)


closer    = process_closer(load_closer_raw())
objetivos = load_objetivos()

all_months = sorted(closer["mes"].dropna().unique(), reverse=True) if not closer.empty else []
sel_month  = st.selectbox("Mes a evaluar", all_months if all_months else ["2026-06"])

c_mes   = closer[closer["mes"] == sel_month] if not closer.empty else pd.DataFrame()
metrics = kpis(c_mes)
obj     = objetivos.get(sel_month, {})

# ── Load / edit objectives ────────────────────────────────────────────────────
with st.expander("✏️ Cargar / editar objetivos del mes", expanded=not obj):
    with st.form("form_objetivos"):
        st.markdown(f"**Objetivos para {sel_month}**")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            obj_revenue = st.number_input("Revenue objetivo (USD)", min_value=0,
                                          value=int(obj.get("revenue", 50000)), step=1000)
            obj_cash    = st.number_input("Cash Collected objetivo (USD)", min_value=0,
                                          value=int(obj.get("cash_collected", 40000)), step=1000)
        with col_b:
            obj_ventas  = st.number_input("Ventas objetivo (#)", min_value=0,
                                          value=int(obj.get("ventas", 20)))
            obj_leads   = st.number_input("Agendas objetivo (#)", min_value=0,
                                          value=int(obj.get("leads", 80)))
        with col_c:
            obj_show    = st.slider("Show rate objetivo (%)", 0, 100,
                                    int(obj.get("show_rate", 0.75) * 100))
            obj_close   = st.slider("Tasa de cierre objetivo (%)", 0, 100,
                                    int(obj.get("close_rate", 0.35) * 100))

        if st.form_submit_button("💾 Guardar objetivos", width='stretch'):
            objetivos[sel_month] = {
                "revenue": obj_revenue, "cash_collected": obj_cash,
                "ventas": obj_ventas,   "leads": obj_leads,
                "show_rate": obj_show / 100, "close_rate": obj_close / 100,
            }
            save_objetivos(objetivos)
            st.success("Objetivos guardados.")
            st.rerun()

obj = objetivos.get(sel_month, {})
if not obj:
    st.info("Cargá los objetivos del mes para ver el avance.")
    st.stop()
if not metrics:
    st.warning("Sin datos del mes seleccionado.")
    st.stop()

st.divider()
st.subheader(f"Avance — {sel_month}")


def progress_card(label, actual, target, fmt="number", col=None):
    pct   = min(actual / target, 1.0) if target else 0
    color = BRAND_GREEN if pct >= 1 else (BRAND_GREY if pct >= 0.7 else "#EB5757")
    actual_str = f"${actual:,.0f}" if fmt == "currency" else (f"{actual:.0%}" if fmt == "pct" else str(int(actual)))
    target_str = f"${target:,.0f}" if fmt == "currency" else (f"{target:.0%}" if fmt == "pct" else str(int(target)))
    c = col if col else st
    c.markdown(
        f"**{label}**  \n{actual_str} / {target_str} — "
        f"<span style='color:{color};font-weight:700'>{pct:.0%}</span>",
        unsafe_allow_html=True,
    )
    c.progress(pct)


col1, col2 = st.columns(2)
progress_card("Revenue",         metrics.get("revenue", 0),         obj.get("revenue", 1),        "currency", col1)
progress_card("Cash Collected",  metrics.get("cash_collected", 0),  obj.get("cash_collected", 1), "currency", col2)
col3, col4 = st.columns(2)
progress_card("Ventas cerradas", metrics.get("compraron", 0),       obj.get("ventas", 1),          "number",   col3)
progress_card("Leads agendados", metrics.get("total_leads", 0),     obj.get("leads", 1),           "number",   col4)
col5, col6 = st.columns(2)
progress_card("Show rate",       metrics.get("show_rate", 0),       obj.get("show_rate", 1),       "pct",      col5)
progress_card("Tasa de cierre",  metrics.get("close_rate", 0),      obj.get("close_rate", 1),      "pct",      col6)

st.divider()

# ── Gauge + Proyección ────────────────────────────────────────────────────────
col_gauge, col_proj = st.columns(2)

with col_gauge:
    st.subheader("Gauge de Revenue")
    rev_actual = metrics.get("revenue", 0)
    rev_target = obj.get("revenue", 1)
    fig_gauge  = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=rev_actual,
        delta={"reference": rev_target, "valueformat": ",.0f",
               "increasing": {"color": BRAND_GREEN}, "decreasing": {"color": "#EB5757"}},
        number={"prefix": "$", "valueformat": ",.0f", "font": {"color": BRAND_GREEN}},
        title={"text": "Revenue USD", "font": {"color": BRAND_WHITE}},
        gauge={
            "axis": {"range": [0, rev_target * 1.2], "tickcolor": BRAND_GREY},
            "bar":  {"color": BRAND_GREEN},
            "bgcolor": "#3A3A3A",
            "steps": [
                {"range": [0, rev_target * 0.7],   "color": "#2A2A2A"},
                {"range": [rev_target * 0.7, rev_target], "color": "#333333"},
            ],
            "threshold": {
                "line": {"color": BRAND_WHITE, "width": 3},
                "thickness": 0.85,
                "value": rev_target,
            },
        },
    ))
    fig_gauge.update_layout(**_dark, height=320)
    st.plotly_chart(fig_gauge, width='stretch')

with col_proj:
    st.subheader("Proyección fin de mes")
    today   = datetime.date.today()
    year, month = int(sel_month[:4]), int(sel_month[5:7])
    days_in_month = calendar.monthrange(year, month)[1]
    day_of_month  = min(today.day, days_in_month) if today.year == year and today.month == month else days_in_month
    days_remaining = max(days_in_month - day_of_month, 0)

    daily_rate = rev_actual / day_of_month if day_of_month else 0
    projected  = rev_actual + daily_rate * days_remaining
    pct_pace   = projected / rev_target if rev_target else 0

    st.metric("Revenue actual",        f"${rev_actual:,.0f}")
    st.metric("Ritmo diario",          f"${daily_rate:,.0f}/día")
    st.metric("Proyección fin de mes", f"${projected:,.0f}",
              delta=f"{pct_pace:.0%} del objetivo",
              delta_color="normal" if pct_pace >= 1 else "inverse")
    st.metric("Días restantes",        days_remaining)

    if pct_pace < 0.8:
        faltan = (rev_target - rev_actual) / max(days_remaining, 1)
        st.error(f"⚠️ Necesitás ${faltan:,.0f}/día para llegar al objetivo.")
    elif pct_pace < 1:
        faltan = (rev_target - rev_actual) / max(days_remaining, 1)
        st.warning(f"Cerca. Necesitás ${faltan:,.0f}/día adicionales.")
    else:
        st.success("✅ En pace para superar el objetivo del mes.")

st.divider()

# ── Histórico ─────────────────────────────────────────────────────────────────
st.subheader("Histórico objetivo vs. real")
hist_data = []
for m, o in objetivos.items():
    c_sub    = closer[closer["mes"] == m] if not closer.empty and "mes" in closer.columns else pd.DataFrame()
    rev_real = c_sub["revenue"].sum() if not c_sub.empty else 0
    hist_data.append({"mes": m, "objetivo": o.get("revenue", 0), "real": rev_real})

if hist_data:
    hist_df = pd.DataFrame(hist_data).sort_values("mes")
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Bar(
        name="Real", x=hist_df["mes"], y=hist_df["real"],
        marker_color=BRAND_GREEN, marker_line_color=BRAND_BLACK, marker_line_width=1,
    ))
    fig_hist.add_trace(go.Scatter(
        name="Objetivo", x=hist_df["mes"], y=hist_df["objetivo"],
        mode="lines+markers",
        line=dict(color=BRAND_WHITE, dash="dash", width=2),
        marker=dict(color=BRAND_WHITE, size=7),
    ))
    fig_hist.update_layout(
        **_dark, height=300,
        legend=dict(bgcolor="#111111"),
        xaxis=dict(gridcolor="#3A3A3A"),
        yaxis=dict(gridcolor="#3A3A3A", title="Revenue USD"),
    )
    st.plotly_chart(fig_hist, width='stretch')
