import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from data.loader import load_triage_raw, load_closer_raw
from processing.triage import process_triage
from processing.closer import process_closer
from processing.funnel import merge_funnel
from config import CLOSER_COLORS, BRAND_GREEN, BRAND_WHITE, BRAND_GREY, BRAND_BLACK
from ui import inject_css, page_header
from auth import require_auth

st.set_page_config(page_title="Vida del Lead", page_icon="🔗", layout="wide")
inject_css()
require_auth()

_dark = dict(paper_bgcolor="#141414", plot_bgcolor="#141414",
             font=dict(color=BRAND_WHITE, family="Inter"), margin=dict(l=10, r=10, t=10, b=10))

page_header("Vida del Lead", "Trazabilidad triage → closing y tiempos de conversión")

triage = process_triage(load_triage_raw())
closer = process_closer(load_closer_raw())
merged = merge_funnel(triage, closer)

if merged.empty:
    st.warning("Sin datos.")
    st.stop()

col1, col2 = st.columns(2)
with col1:
    all_months = sorted(merged["mes"].dropna().unique(), reverse=True) if "mes" in merged.columns else []
    sel_month  = st.selectbox("Mes", ["Todos"] + list(all_months))
with col2:
    all_closers = sorted(merged["closer"].dropna().unique()) if "closer" in merged.columns else []
    sel_closer  = st.multiselect("Closer", all_closers, default=all_closers)

if sel_month != "Todos" and "mes" in merged.columns:
    merged = merged[merged["mes"] == sel_month]
if sel_closer and "closer" in merged.columns:
    merged = merged[merged["closer"].isin(sel_closer)]

# ── Tiempo de vida del lead ───────────────────────────────────────────────────
st.subheader("Tiempo de vida del lead (triage → closing)")
if "dias_triage_a_closing" in merged.columns:
    dias_df = merged[merged["dias_triage_a_closing"].notna() & (merged["dias_triage_a_closing"] >= 0)]
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Tiempo promedio", f"{dias_df['dias_triage_a_closing'].mean():.1f} días" if not dias_df.empty else "—")
    col_b.metric("Tiempo mediano",  f"{dias_df['dias_triage_a_closing'].median():.1f} días" if not dias_df.empty else "—")
    col_c.metric("Leads cruzados",  len(dias_df))

    if not dias_df.empty:
        fig_hist = px.histogram(
            dias_df, x="dias_triage_a_closing",
            color="closer" if "closer" in dias_df.columns else None,
            color_discrete_map=CLOSER_COLORS,
            nbins=20,
            labels={"dias_triage_a_closing": "Días desde triage hasta closing"},
        )
        fig_hist.update_traces(marker_line_color=BRAND_BLACK, marker_line_width=1)
        fig_hist.update_layout(**_dark, height=300,
                                xaxis=dict(gridcolor="#3A3A3A"),
                                yaxis=dict(gridcolor="#3A3A3A"),
                                legend=dict(bgcolor="#111111"))
        st.plotly_chart(fig_hist, width='stretch')
else:
    st.info("No hay suficientes datos cruzados. Verificá que los emails/teléfonos coincidan entre triage y tracker.")

st.divider()

# ── Por día de la semana ──────────────────────────────────────────────────────
day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
day_names = {"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles",
             "Thursday":"Jueves","Friday":"Viernes","Saturday":"Sábado","Sunday":"Domingo"}

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Show rate por día")
    if "dia_semana" in merged.columns and "asistio" in merged.columns:
        dg = (merged.groupby("dia_semana")
              .agg(total=("lead","count"), asistieron=("asistio","sum")).reset_index())
        dg["show_rate"] = dg["asistieron"] / dg["total"]
        dg["orden"]     = dg["dia_semana"].map(lambda d: day_order.index(d) if d in day_order else 99)
        dg = dg.sort_values("orden")
        dg["dia_es"] = dg["dia_semana"].map(day_names)

        fig = go.Figure(go.Bar(
            x=dg["dia_es"], y=dg["show_rate"],
            text=dg["show_rate"].apply(lambda v: f"{v:.0%}"),
            textposition="outside",
            textfont=dict(color=BRAND_WHITE),
            marker=dict(
                color=dg["show_rate"],
                colorscale=[[0, "#3A3A3A"], [1, BRAND_GREEN]],
                line=dict(color=BRAND_BLACK, width=1),
            ),
        ))
        fig.update_layout(**_dark, height=310, yaxis_tickformat=".0%",
                           yaxis=dict(gridcolor="#3A3A3A"),
                           coloraxis_showscale=False)
        st.plotly_chart(fig, width='stretch')

with col_right:
    st.subheader("Tasa de cierre por día")
    if "dia_semana" in merged.columns and "compro" in merged.columns:
        cg = (merged.groupby("dia_semana")
              .agg(calificaron=("califico","sum"), compraron=("compro","sum")).reset_index())
        cg["close_rate"] = cg.apply(lambda r: r["compraron"]/r["calificaron"] if r["calificaron"] >= 2 else 0, axis=1)
        cg["orden"]  = cg["dia_semana"].map(lambda d: day_order.index(d) if d in day_order else 99)
        cg = cg.sort_values("orden")
        cg["dia_es"] = cg["dia_semana"].map(day_names)

        fig2 = go.Figure(go.Bar(
            x=cg["dia_es"], y=cg["close_rate"],
            text=cg["close_rate"].apply(lambda v: f"{v:.0%}"),
            textposition="outside",
            textfont=dict(color=BRAND_WHITE),
            marker=dict(
                color=cg["close_rate"],
                colorscale=[[0, "#3A3A3A"], [1, BRAND_GREEN]],
                line=dict(color=BRAND_BLACK, width=1),
            ),
        ))
        fig2.update_layout(**_dark, height=310, yaxis_tickformat=".0%",
                            yaxis=dict(gridcolor="#3A3A3A"),
                            coloraxis_showscale=False)
        st.plotly_chart(fig2, width='stretch')

st.divider()

# ── Buscador de lead ──────────────────────────────────────────────────────────
st.subheader("Buscar lead — timeline individual")
search = st.text_input("Nombre o email")
if search:
    mask   = merged["lead"].str.contains(search, case=False, na=False)
    if "email_key" in merged.columns:
        mask |= merged["email_key"].str.contains(search, case=False, na=False)
    result = merged[mask]
    if result.empty:
        st.info("No encontrado.")
    else:
        for _, row in result.iterrows():
            fecha_str = row["fecha"].strftime("%d/%m/%Y") if pd.notna(row.get("fecha")) else "?"
            with st.expander(f"**{row.get('lead','?')}** — {fecha_str}"):
                stages = []
                if "fecha_agenda_t" in row and pd.notna(row["fecha_agenda_t"]):
                    stages.append(f"📅 Agendado ({str(row['fecha_agenda_t'])[:10]})")
                stages.append(f"📞 Sesión ({fecha_str})")
                stages.append("✅ Asistió" if row.get("asistio") else "❌ No asistió")
                stages.append("✅ Calificó" if row.get("califico") else "❌ No calificó")
                stages.append("🏆 Compró" if row.get("compro") else "⏳ Sin cierre")
                st.markdown(
                    " → ".join(
                        f"<span style='color:{BRAND_GREEN if '✅' in s or '🏆' in s else (BRAND_WHITE if '📅' in s or '📞' in s else BRAND_GREY)}'>{s}</span>"
                        for s in stages
                    ),
                    unsafe_allow_html=True,
                )
                c1, c2, c3 = st.columns(3)
                c1.write(f"**Closer:** {row.get('closer','—')}")
                c2.write(f"**Revenue:** ${row.get('revenue',0):,.0f}")
                c3.write(f"**Pago:** {row.get('medio_pago','—')}")
                if row.get("notas"):
                    st.caption(f"Notas: {row['notas']}")
                if "dias_triage_a_closing" in row and pd.notna(row["dias_triage_a_closing"]):
                    st.caption(f"Tiempo triage→closing: {int(row['dias_triage_a_closing'])} días")

st.divider()

# ── Leads en seguimiento ──────────────────────────────────────────────────────
st.subheader("Leads en seguimiento activo")
if "estado_seguimiento" in merged.columns:
    seg_estados = ["Continuar Seguim","TRIAGGE - SEGUIMIENTO","Ampliable"]
    seg = merged[merged["estado_seguimiento"].str.strip().isin(seg_estados)].copy()
    if not seg.empty:
        cols_s = ["fecha","lead","closer","estado_seguimiento","califico","compro","notas"]
        avail  = [col for col in cols_s if col in seg.columns]
        st.dataframe(seg[avail].sort_values("fecha", ascending=False),
                     width='stretch', hide_index=True)
        st.caption(f"{len(seg)} leads con seguimiento pendiente")
    else:
        st.success("Sin leads en seguimiento activo para este período.")
