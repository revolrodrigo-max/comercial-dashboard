import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from data.loader import load_triage_raw, load_closer_raw
from processing.triage import process_triage
from processing.closer import process_closer
from processing.funnel import merge_funnel
from config import CLOSER_COLORS

st.set_page_config(page_title="Vida del Lead", page_icon="🔗", layout="wide")
st.title("🔗 Vida del Lead — Triage → Closing")

triage = process_triage(load_triage_raw())
closer = process_closer(load_closer_raw())
merged = merge_funnel(triage, closer)

if merged.empty:
    st.warning("Sin datos para mostrar el journey.")
    st.stop()

# ── Filters ───────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    all_months = sorted(merged["mes"].dropna().unique(), reverse=True) if "mes" in merged else []
    sel_month = st.selectbox("Mes", ["Todos"] + list(all_months))
with col2:
    all_closers = sorted(merged["closer"].dropna().unique()) if "closer" in merged else []
    sel_closer = st.multiselect("Closer", all_closers, default=all_closers)

if sel_month != "Todos" and "mes" in merged.columns:
    merged = merged[merged["mes"] == sel_month]
if sel_closer and "closer" in merged.columns:
    merged = merged[merged["closer"].isin(sel_closer)]

# ── Time from triage to closing ────────────────────────────────────────────────
st.subheader("Tiempo de vida del lead (triage → closing)")

if "dias_triage_a_closing" in merged.columns:
    dias_df = merged[merged["dias_triage_a_closing"].notna() & (merged["dias_triage_a_closing"] >= 0)]

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Tiempo promedio", f"{dias_df['dias_triage_a_closing'].mean():.1f} días")
    col_b.metric("Tiempo mediano", f"{dias_df['dias_triage_a_closing'].median():.1f} días")
    col_c.metric("Leads con triage matching", len(dias_df))

    if not dias_df.empty:
        fig_hist = px.histogram(
            dias_df, x="dias_triage_a_closing",
            color="closer" if "closer" in dias_df.columns else None,
            color_discrete_map=CLOSER_COLORS,
            nbins=20,
            labels={"dias_triage_a_closing": "Días desde triage hasta closing"},
        )
        fig_hist.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_hist, use_container_width=True)
else:
    st.info("No hay suficientes datos cruzados para calcular tiempos. Verificá que los emails/teléfonos coincidan entre triage y tracker.")

st.divider()

# ── Funnel by day of week ─────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Show rate por día de la semana")
    if "dia_semana" in merged.columns and "asistio" in merged.columns:
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_names = {"Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
                     "Thursday": "Jueves", "Friday": "Viernes",
                     "Saturday": "Sábado", "Sunday": "Domingo"}

        day_grp = (
            merged.groupby("dia_semana")
            .agg(total=("lead", "count"), asistieron=("asistio", "sum"))
            .reset_index()
        )
        day_grp["show_rate"] = day_grp["asistieron"] / day_grp["total"]
        day_grp["orden"] = day_grp["dia_semana"].map(lambda d: day_order.index(d) if d in day_order else 99)
        day_grp = day_grp.sort_values("orden")
        day_grp["dia_es"] = day_grp["dia_semana"].map(day_names)

        fig_dow = px.bar(
            day_grp, x="dia_es", y="show_rate",
            text=day_grp["show_rate"].apply(lambda v: f"{v:.0%}"),
            color="show_rate",
            color_continuous_scale="RdYlGn",
            labels={"dia_es": "", "show_rate": "Show rate"},
        )
        fig_dow.update_traces(textposition="outside")
        fig_dow.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0),
                               coloraxis_showscale=False, yaxis_tickformat=".0%")
        st.plotly_chart(fig_dow, use_container_width=True)

with col_right:
    st.subheader("Tasa de cierre por día de la semana")
    if "dia_semana" in merged.columns and "compro" in merged.columns:
        close_dow = (
            merged.groupby("dia_semana")
            .agg(calificaron=("califico", "sum"), compraron=("compro", "sum"))
            .reset_index()
        )
        close_dow["close_rate"] = close_dow.apply(
            lambda r: r["compraron"] / r["calificaron"] if r["calificaron"] else 0, axis=1
        )
        close_dow["orden"] = close_dow["dia_semana"].map(
            lambda d: ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"].index(d)
            if d in ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"] else 99
        )
        close_dow = close_dow.sort_values("orden")
        day_names_map = {"Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
                         "Thursday": "Jueves", "Friday": "Viernes",
                         "Saturday": "Sábado", "Sunday": "Domingo"}
        close_dow["dia_es"] = close_dow["dia_semana"].map(day_names_map)

        fig_cdow = px.bar(
            close_dow, x="dia_es", y="close_rate",
            text=close_dow["close_rate"].apply(lambda v: f"{v:.0%}"),
            color="close_rate",
            color_continuous_scale="RdYlGn",
            labels={"dia_es": "", "close_rate": "Tasa de cierre"},
        )
        fig_cdow.update_traces(textposition="outside")
        fig_cdow.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0),
                                coloraxis_showscale=False, yaxis_tickformat=".0%")
        st.plotly_chart(fig_cdow, use_container_width=True)

st.divider()

# ── Lead search ───────────────────────────────────────────────────────────────
st.subheader("Buscar lead — timeline individual")
search = st.text_input("Nombre o email del lead")

if search:
    mask = merged["lead"].str.contains(search, case=False, na=False)
    if "email_key" in merged.columns:
        mask |= merged["email_key"].str.contains(search, case=False, na=False)
    result = merged[mask]

    if result.empty:
        st.info("No se encontró el lead.")
    else:
        for _, row in result.iterrows():
            with st.expander(f"**{row.get('lead', '?')}** — {row.get('fecha', '').strftime('%d/%m/%Y') if pd.notna(row.get('fecha')) else '?'}"):
                stages = []

                if "fecha_agenda_t" in row and pd.notna(row["fecha_agenda_t"]):
                    stages.append(("📅 Agendado (triage)", str(row["fecha_agenda_t"])[:10]))
                if pd.notna(row.get("fecha")):
                    stages.append(("📞 Sesión closing", str(row["fecha"])[:10]))

                asistio = row.get("asistio", False)
                stages.append(("✅ Asistió" if asistio else "❌ No asistió", ""))

                califico = row.get("califico", False)
                stages.append(("✅ Calificó" if califico else "❌ No calificó", ""))

                compro = row.get("compro", False)
                stages.append(("🏆 Compró" if compro else "⏳ No compró aún", ""))

                timeline_md = " → ".join([s[0] for s in stages])
                st.markdown(timeline_md)

                c1, c2, c3 = st.columns(3)
                c1.write(f"**Closer:** {row.get('closer', '—')}")
                c2.write(f"**Revenue:** ${row.get('revenue', 0):,.0f}")
                c3.write(f"**Pago:** {row.get('tipo_pago', '—')}")

                if row.get("notas"):
                    st.caption(f"Notas: {row['notas']}")
                if "dias_triage_a_closing" in row and pd.notna(row["dias_triage_a_closing"]):
                    st.caption(f"Tiempo triage→closing: {int(row['dias_triage_a_closing'])} días")

st.divider()

# ── Leads en seguimiento ──────────────────────────────────────────────────────
st.subheader("Leads en seguimiento activo")
if "estado_seguimiento" in merged.columns:
    seguimiento_estados = ["Continuar Seguim", "TRIAGGE - SEGUIMIENTO", "Ampliable"]
    seguimiento = merged[
        merged["estado_seguimiento"].str.strip().isin(seguimiento_estados)
    ].copy()

    if not seguimiento.empty:
        show_cols = ["fecha", "lead", "closer", "estado_seguimiento",
                     "califico", "compro", "notas"]
        avail = [col for col in show_cols if col in seguimiento.columns]
        st.dataframe(
            seguimiento[avail].sort_values("fecha", ascending=False),
            use_container_width=True, hide_index=True
        )
        st.caption(f"{len(seguimiento)} leads con seguimiento pendiente")
    else:
        st.success("Sin leads en seguimiento activo para este período.")
