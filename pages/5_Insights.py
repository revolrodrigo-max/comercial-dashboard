import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from collections import Counter
import re

from data.loader import load_triage_raw, load_closer_raw
from processing.triage import process_triage
from processing.closer import process_closer
from processing.funnel import merge_funnel, kpis
from config import BRAND_GREEN, BRAND_WHITE, BRAND_GREY, BRAND_BLACK, BRAND_SCALE

st.set_page_config(page_title="Insights", page_icon="💡", layout="wide")

st.markdown("""
<style>
[data-testid="stMetricValue"] { color: #C7FF00; font-weight: 700; }
[data-testid="stMetricLabel"] { color: #6B6969; text-transform: uppercase; font-size:.75rem; }
</style>
""", unsafe_allow_html=True)

_dark = dict(paper_bgcolor="#111111", plot_bgcolor="#111111",
             font=dict(color=BRAND_WHITE), margin=dict(l=0, r=0, t=10, b=0))

st.markdown("<h1 style='color:#FFFFFF'>💡 Insights Automáticos</h1>", unsafe_allow_html=True)

triage  = process_triage(load_triage_raw())
closer  = process_closer(load_closer_raw())
merged  = merge_funnel(triage, closer)

all_months = sorted(closer["mes"].dropna().unique(), reverse=True) if not closer.empty else []
sel_month  = st.selectbox("Mes", ["Todos"] + list(all_months))

c = closer[closer["mes"] == sel_month].copy() if sel_month != "Todos" and not closer.empty else closer.copy()
m = merged[merged["mes"] == sel_month].copy() if sel_month != "Todos" and "mes" in merged.columns else merged.copy()

metrics = kpis(c)
if not metrics:
    st.warning("Sin datos.")
    st.stop()

# ── Auto insights ─────────────────────────────────────────────────────────────
insights = []

if "closer" in c.columns and c["closer"].notna().any():
    grp = c.groupby("closer").agg(
        calificaron=("califico", "sum"), compraron=("compro", "sum"), revenue=("revenue", "sum")
    ).reset_index()
    grp["close_rate"] = grp.apply(lambda r: r["compraron"] / r["calificaron"] if r["calificaron"] >= 3 else None, axis=1)
    gv = grp.dropna(subset=["close_rate"])
    if len(gv) >= 2:
        best  = gv.loc[gv["close_rate"].idxmax()]
        worst = gv.loc[gv["close_rate"].idxmin()]
        insights.append({"icon": "🏆", "tipo": "Performance",
            "titulo": f"{best['closer']} lidera con {best['close_rate']:.0%} de cierre",
            "detalle": f"Vs {worst['closer']} con {worst['close_rate']:.0%}. Gap: {best['close_rate']-worst['close_rate']:.0%}.",
            "border": BRAND_GREEN})

if "califico" in c.columns and "compro" in c.columns:
    hot = c[(c["califico"] == True) & (c["compro"] == False)]
    if not hot.empty:
        pot = len(hot) * metrics.get("ticket_promedio", 2500)
        insights.append({"icon": "🔥", "tipo": "Oportunidad",
            "titulo": f"{len(hot)} leads calificados sin cerrar",
            "detalle": f"Revenue potencial estimado: ${pot:,.0f}",
            "border": BRAND_GREEN})

show_r = metrics.get("show_rate", 0)
if show_r < 0.65:
    insights.append({"icon": "⚠️", "tipo": "Alerta",
        "titulo": f"Show rate bajo: {show_r:.0%}",
        "detalle": "Por debajo del 65%. Revisá el proceso de confirmación.",
        "border": "#EB5757"})
elif show_r >= 0.80:
    insights.append({"icon": "✅", "tipo": "Fortaleza",
        "titulo": f"Show rate excelente: {show_r:.0%}",
        "detalle": "La confirmación de agendas funciona muy bien.",
        "border": BRAND_GREEN})

if "dia_semana" in c.columns and "compro" in c.columns:
    dg = c.groupby("dia_semana").agg(calificaron=("califico","sum"), compraron=("compro","sum")).reset_index()
    dg["cr"] = dg.apply(lambda r: r["compraron"]/r["calificaron"] if r["calificaron"] >= 2 else None, axis=1)
    dv = dg.dropna(subset=["cr"])
    if not dv.empty:
        best_day = dv.loc[dv["cr"].idxmax()]
        day_map  = {"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles",
                    "Thursday":"Jueves","Friday":"Viernes","Saturday":"Sábado","Sunday":"Domingo"}
        insights.append({"icon": "📅", "tipo": "Timing",
            "titulo": f"Mejor día para cerrar: {day_map.get(best_day['dia_semana'], best_day['dia_semana'])}",
            "detalle": f"Tasa de cierre de {best_day['cr']:.0%} ese día.",
            "border": BRAND_GREY})

rev  = metrics.get("revenue", 0)
cash = metrics.get("cash_collected", 0)
if rev > 0 and (rev - cash) / rev > 0.3:
    insights.append({"icon": "💸", "tipo": "Cobranza",
        "titulo": f"Gap revenue vs cash: ${rev-cash:,.0f} ({(rev-cash)/rev:.0%})",
        "detalle": "Revisá pagos en cuotas y cobros pendientes.",
        "border": BRAND_GREY})

if "dias_triage_a_closing" in m.columns:
    vd = m[m["dias_triage_a_closing"].notna() & (m["dias_triage_a_closing"] >= 0)]
    if not vd.empty:
        avg_days = vd["dias_triage_a_closing"].mean()
        same_day = (vd["dias_triage_a_closing"] <= 1).sum()
        insights.append({"icon": "⏱️", "tipo": "Velocidad",
            "titulo": f"Tiempo promedio triage→closing: {avg_days:.1f} días",
            "detalle": f"{same_day} leads cerraron el mismo día o al siguiente.",
            "border": BRAND_GREEN})

# ── Render insights ───────────────────────────────────────────────────────────
if not insights:
    st.info("Sin suficientes datos para generar insights en este período.")
else:
    cols = st.columns(2)
    for i, ins in enumerate(insights):
        with cols[i % 2]:
            st.markdown(
                f"<div style='border-left:3px solid {ins['border']};background:#111111;"
                f"border-radius:6px;padding:16px;margin-bottom:14px'>"
                f"<span style='font-size:1.4em'>{ins['icon']}</span> "
                f"<span style='font-size:.72rem;color:#6B6969;text-transform:uppercase;letter-spacing:.07em'>{ins['tipo']}</span><br>"
                f"<b style='color:#FFFFFF'>{ins['titulo']}</b><br>"
                f"<span style='color:#6B6969;font-size:.88em'>{ins['detalle']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

st.divider()

# ── Hot leads ─────────────────────────────────────────────────────────────────
st.subheader("🔥 Leads calificados sin cerrar")
if "califico" in c.columns and "compro" in c.columns:
    hot = c[(c["califico"] == True) & (c["compro"] == False)].copy()
    if not hot.empty:
        cols_show = ["fecha", "lead", "closer", "estado_seguimiento", "notas", "celular", "email"]
        avail = [col for col in cols_show if col in hot.columns]
        st.dataframe(hot[avail].sort_values("fecha", ascending=False),
                     use_container_width=True, hide_index=True)
    else:
        st.success("Todos los leads calificados compraron. 💪")

st.divider()

# ── Palabras clave en notas ───────────────────────────────────────────────────
st.subheader("📝 Palabras clave en notas")
if "notas" in c.columns:
    all_notes = " ".join(c["notas"].dropna().tolist()).lower()
    stopwords = {"de","la","el","en","y","a","que","se","con","para","no","un","una",
                 "es","lo","por","me","le","su","del","al","los","las","pero","como",
                 "más","si","ya","fue","hay","porque","todo","este","esta","tiene",
                 "hacer","puede","así","cuando","también","mi","o","sobre","ha",
                 "pago","link","stripe","transfer"}
    words = re.findall(r"\b[a-záéíóúñü]{4,}\b", all_notes)
    freq  = Counter(w for w in words if w not in stopwords)
    top   = pd.DataFrame(freq.most_common(20), columns=["palabra", "frecuencia"])
    if not top.empty:
        fig_words = go.Figure(go.Bar(
            x=top["frecuencia"], y=top["palabra"], orientation="h",
            marker=dict(
                color=top["frecuencia"],
                colorscale=[[0, BRAND_GREY], [1, BRAND_GREEN]],
                line=dict(color=BRAND_BLACK, width=1),
            ),
            textfont=dict(color=BRAND_WHITE),
        ))
        fig_words.update_layout(**_dark, height=460,
                                 yaxis=dict(autorange="reversed"),
                                 xaxis=dict(gridcolor="#3A3A3A"))
        st.plotly_chart(fig_words, use_container_width=True)

st.divider()

# ── Perfil del lead ───────────────────────────────────────────────────────────
st.subheader("👤 Perfil del lead — ocupaciones")
t_f = triage if triage.empty else (
    triage[triage["mes"] == sel_month] if sel_month != "Todos" and "mes" in triage.columns else triage
)
if not t_f.empty and "ocupacion" in t_f.columns:
    ocup = (t_f["ocupacion"].dropna().str.strip().str.title()
            .value_counts().head(15).reset_index())
    ocup.columns = ["ocupacion", "cantidad"]
    fig_ocup = go.Figure(go.Bar(
        x=ocup["cantidad"], y=ocup["ocupacion"], orientation="h",
        marker=dict(color=BRAND_GREEN, line=dict(color=BRAND_BLACK, width=1)),
        textfont=dict(color=BRAND_WHITE),
    ))
    fig_ocup.update_layout(**_dark, height=420,
                            yaxis=dict(autorange="reversed"),
                            xaxis=dict(gridcolor="#3A3A3A"))
    st.plotly_chart(fig_ocup, use_container_width=True)
