import streamlit as st
import plotly.express as px
import pandas as pd
from collections import Counter
import re

from data.loader import load_triage_raw, load_closer_raw
from processing.triage import process_triage
from processing.closer import process_closer
from processing.funnel import merge_funnel, kpis

st.set_page_config(page_title="Insights", page_icon="💡", layout="wide")
st.title("💡 Insights Automáticos")

triage = process_triage(load_triage_raw())
closer = process_closer(load_closer_raw())
merged = merge_funnel(triage, closer)

all_months = sorted(closer["mes"].dropna().unique(), reverse=True) if not closer.empty else []
sel_month = st.selectbox("Mes", ["Todos"] + list(all_months))

if sel_month != "Todos":
    c = closer[closer["mes"] == sel_month].copy()
    m = merged[merged["mes"] == sel_month].copy() if "mes" in merged.columns else merged.copy()
else:
    c = closer.copy()
    m = merged.copy()

metrics = kpis(c)

if not metrics:
    st.warning("Sin datos.")
    st.stop()

# ── Auto-generated insights ───────────────────────────────────────────────────
insights = []

# 1. Best/worst closer by close rate
if "closer" in c.columns and c["closer"].notna().any():
    grp = c.groupby("closer").agg(
        calificaron=("califico", "sum"),
        compraron=("compro", "sum"),
        revenue=("revenue", "sum"),
    ).reset_index()
    grp["close_rate"] = grp.apply(
        lambda r: r["compraron"] / r["calificaron"] if r["calificaron"] >= 3 else None, axis=1
    )
    grp_valid = grp.dropna(subset=["close_rate"])
    if len(grp_valid) >= 2:
        best = grp_valid.loc[grp_valid["close_rate"].idxmax()]
        worst = grp_valid.loc[grp_valid["close_rate"].idxmin()]
        insights.append({
            "icon": "🏆",
            "tipo": "Performance",
            "titulo": f"{best['closer']} lidera con {best['close_rate']:.0%} de cierre",
            "detalle": f"Vs. {worst['closer']} con {worst['close_rate']:.0%}. Diferencia de {best['close_rate']-worst['close_rate']:.0%}.",
            "color": "#E8F5E9",
        })

# 2. Leads qualified but not closed (follow-up opportunities)
if "califico" in c.columns and "compro" in c.columns:
    hot_leads = c[(c["califico"] == True) & (c["compro"] == False)].copy()
    if not hot_leads.empty:
        insights.append({
            "icon": "🔥",
            "tipo": "Oportunidad",
            "titulo": f"{len(hot_leads)} leads calificados sin cerrar",
            "detalle": f"Revenue potencial estimado: ${len(hot_leads) * metrics.get('ticket_promedio', 2500):,.0f}",
            "color": "#FFF3E0",
        })

# 3. Show rate alert
show_r = metrics.get("show_rate", 0)
if show_r < 0.65:
    insights.append({
        "icon": "⚠️",
        "tipo": "Alerta",
        "titulo": f"Show rate bajo: {show_r:.0%}",
        "detalle": "La tasa de asistencia está por debajo del 65%. Revisá el proceso de confirmación.",
        "color": "#FFEBEE",
    })
elif show_r >= 0.80:
    insights.append({
        "icon": "✅",
        "tipo": "Fortaleza",
        "titulo": f"Excelente show rate: {show_r:.0%}",
        "detalle": "La confirmación de agendas está funcionando muy bien.",
        "color": "#E8F5E9",
    })

# 4. Best day of week for closing
if "dia_semana" in c.columns and "compro" in c.columns:
    day_close = c.groupby("dia_semana").agg(
        calificaron=("califico", "sum"), compraron=("compro", "sum")
    ).reset_index()
    day_close["close_rate"] = day_close.apply(
        lambda r: r["compraron"] / r["calificaron"] if r["calificaron"] >= 2 else None, axis=1
    )
    valid = day_close.dropna(subset=["close_rate"])
    if not valid.empty:
        best_day = valid.loc[valid["close_rate"].idxmax()]
        day_map = {"Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
                   "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"}
        insights.append({
            "icon": "📅",
            "tipo": "Timing",
            "titulo": f"Mejor día para cerrar: {day_map.get(best_day['dia_semana'], best_day['dia_semana'])}",
            "detalle": f"Tasa de cierre de {best_day['close_rate']:.0%} ese día.",
            "color": "#E3F2FD",
        })

# 5. Revenue vs cash gap
rev = metrics.get("revenue", 0)
cash = metrics.get("cash_collected", 0)
if rev > 0:
    gap = rev - cash
    gap_pct = gap / rev
    if gap_pct > 0.3:
        insights.append({
            "icon": "💸",
            "tipo": "Cobranza",
            "titulo": f"Gap revenue vs. cash: ${gap:,.0f} ({gap_pct:.0%})",
            "detalle": "Hay revenue comprometido que aún no entró como cash. Revisá pagos en cuotas pendientes.",
            "color": "#FFF8E1",
        })

# 6. Upsells
if "es_upsell" in c.columns and c["es_upsell"].sum() > 0:
    upsells = c[c["es_upsell"] == True]
    insights.append({
        "icon": "📈",
        "tipo": "Upsell",
        "titulo": f"{len(upsells)} upsells en el período",
        "detalle": f"Revenue de upsells: ${upsells['revenue'].sum():,.0f}",
        "color": "#F3E5F5",
    })

# 7. Time to close
if "dias_triage_a_closing" in m.columns:
    valid_days = m[m["dias_triage_a_closing"].notna() & (m["dias_triage_a_closing"] >= 0)]
    if not valid_days.empty:
        avg_days = valid_days["dias_triage_a_closing"].mean()
        fast_closes = valid_days[valid_days["dias_triage_a_closing"] <= 1]
        insights.append({
            "icon": "⏱️",
            "tipo": "Velocidad",
            "titulo": f"Tiempo promedio triage→closing: {avg_days:.1f} días",
            "detalle": f"{len(fast_closes)} leads cerraron el mismo día o al día siguiente del triage.",
            "color": "#E8F5E9",
        })

# ── Display insights ──────────────────────────────────────────────────────────
if not insights:
    st.info("Sin insights suficientes para este período. Necesitás más datos.")
else:
    cols = st.columns(2)
    for i, ins in enumerate(insights):
        with cols[i % 2]:
            st.markdown(
                f"<div style='background:{ins['color']};border-radius:8px;padding:16px;margin-bottom:12px'>"
                f"<span style='font-size:1.5em'>{ins['icon']}</span> "
                f"<span style='font-size:0.75em;color:#666;text-transform:uppercase'>{ins['tipo']}</span><br>"
                f"<b>{ins['titulo']}</b><br>"
                f"<span style='color:#555;font-size:0.9em'>{ins['detalle']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

st.divider()

# ── Hot leads: calificaron pero no compraron ──────────────────────────────────
st.subheader("🔥 Leads calificados sin cerrar — acción recomendada")
if "califico" in c.columns and "compro" in c.columns:
    hot = c[(c["califico"] == True) & (c["compro"] == False)].copy()
    if not hot.empty:
        show_cols = ["fecha", "lead", "closer", "estado_seguimiento", "notas",
                     "motivo_cancelacion", "celular", "email"]
        avail = [col for col in show_cols if col in hot.columns]
        st.dataframe(hot[avail].sort_values("fecha", ascending=False),
                     use_container_width=True, hide_index=True)
    else:
        st.success("Todos los leads calificados compraron. 💪")

st.divider()

# ── Common objections from notes ──────────────────────────────────────────────
st.subheader("📝 Palabras clave en notas (objeciones y contexto)")
if "notas" in c.columns:
    all_notes = " ".join(c["notas"].dropna().tolist()).lower()

    # Remove common Spanish stopwords
    stopwords = {
        "de", "la", "el", "en", "y", "a", "que", "se", "con", "para", "no",
        "un", "una", "es", "lo", "por", "me", "le", "su", "del", "al", "los",
        "las", "pero", "como", "más", "si", "ya", "fue", "hay", "porque",
        "todo", "este", "esta", "tiene", "hacer", "puede", "así", "cuando",
        "también", "mi", "o", "sobre", "ha", "pago", "link", "stripe",
    }

    words = re.findall(r"\b[a-záéíóúñü]{4,}\b", all_notes)
    word_freq = Counter(w for w in words if w not in stopwords)
    top_words = pd.DataFrame(word_freq.most_common(30), columns=["palabra", "frecuencia"])

    if not top_words.empty:
        fig_words = px.bar(
            top_words.head(20), x="frecuencia", y="palabra",
            orientation="h",
            color="frecuencia",
            color_continuous_scale="Blues",
        )
        fig_words.update_layout(height=450, margin=dict(l=0, r=0, t=10, b=0),
                                 coloraxis_showscale=False, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_words, use_container_width=True)

st.divider()

# ── Ocupaciones más frecuentes (de triage) ───────────────────────────────────
st.subheader("👤 Perfil del lead — ocupaciones frecuentes")
triage_filtered = triage if triage.empty else (
    triage[triage["mes"] == sel_month] if sel_month != "Todos" and "mes" in triage.columns else triage
)
if not triage_filtered.empty and "ocupacion" in triage_filtered.columns:
    ocup = (
        triage_filtered["ocupacion"]
        .dropna()
        .str.strip()
        .str.title()
        .value_counts()
        .head(15)
        .reset_index()
    )
    ocup.columns = ["ocupacion", "cantidad"]
    fig_ocup = px.bar(ocup, x="cantidad", y="ocupacion", orientation="h",
                      color_discrete_sequence=["#4C9BE8"])
    fig_ocup.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0),
                            yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_ocup, use_container_width=True)
