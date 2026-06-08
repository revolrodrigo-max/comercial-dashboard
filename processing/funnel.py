"""
Merges triage + closer tracker to build the complete lead lifecycle.
Join key priority: email → phone → name (last resort).
"""

import pandas as pd
import numpy as np


def _build_key(df: pd.DataFrame, email_col: str, phone_col: str) -> pd.Series:
    """Return best available join key per row."""
    email = df[email_col].str.lower().str.strip().fillna("")
    phone = df[phone_col].fillna("")
    return email.where(email != "", phone)


def merge_funnel(triage: pd.DataFrame, closer: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a lead-level DataFrame with columns from both sources.
    One row per closing-tracker entry; triage columns added where matched.
    """
    if closer.empty:
        return pd.DataFrame()

    t = triage.copy() if not triage.empty else pd.DataFrame()
    c = closer.copy()

    if not t.empty:
        t["_key"] = _build_key(t, "email_key", "phone_key")
        c["_key"] = _build_key(c, "email_key", "phone_key")

        triage_cols = [
            "_key", "fecha_agenda", "asistio", "califico",
            "fue_a_closing", "vendio", "ticket", "cash_collected",
            "ocupacion", "notas", "closer_triage",
        ]
        available = [col for col in triage_cols if col in t.columns]
        t_slim = t[available].copy()
        t_slim = t_slim[t_slim["_key"] != ""].drop_duplicates("_key")

        merged = c.merge(
            t_slim.add_suffix("_t").rename(columns={"_key_t": "_key"}),
            on="_key",
            how="left",
        )
    else:
        merged = c.copy()
        merged["fecha_agenda_t"] = pd.NaT

    # Derived: days from triage agenda to closing call
    if "fecha_agenda_t" in merged.columns:
        merged["dias_triage_a_closing"] = (
            merged["fecha"] - pd.to_datetime(merged["fecha_agenda_t"])
        ).dt.days

    return merged.drop(columns=["_key"], errors="ignore")


def funnel_counts(df_source: pd.DataFrame, source: str = "closer") -> pd.DataFrame:
    """
    Returns stage counts for a funnel chart.
    source: 'closer' or 'triage'
    """
    if source == "closer":
        total = len(df_source)
        asistieron = df_source["asistio"].sum() if "asistio" in df_source else 0
        calificaron = df_source["califico"].sum() if "califico" in df_source else 0
        compraron = df_source["compro"].sum() if "compro" in df_source else 0
    else:
        total = len(df_source)
        asistieron = df_source["asistio"].sum() if "asistio" in df_source else 0
        calificaron = df_source["califico"].sum() if "califico" in df_source else 0
        compraron = df_source["vendio"].sum() if "vendio" in df_source else 0

    return pd.DataFrame({
        "etapa": ["Agendados", "Asistieron", "Calificaron", "Compraron"],
        "cantidad": [int(total), int(asistieron), int(calificaron), int(compraron)],
    })


def kpis(closer: pd.DataFrame) -> dict:
    """Compute top-level KPIs from the closer tracker."""
    if closer.empty:
        return {}

    total_leads = len(closer)
    asistieron = closer["asistio"].sum()
    calificaron = closer["califico"].sum()
    compraron = closer["compro"].sum()
    revenue = closer["revenue"].sum()
    cash = closer["cash_collected"].sum()

    show_rate = asistieron / total_leads if total_leads else 0
    calif_rate = calificaron / asistieron if asistieron else 0
    close_rate = compraron / calificaron if calificaron else 0
    ticket_prom = revenue / compraron if compraron else 0

    return {
        "total_leads": int(total_leads),
        "asistieron": int(asistieron),
        "calificaron": int(calificaron),
        "compraron": int(compraron),
        "revenue": revenue,
        "cash_collected": cash,
        "show_rate": show_rate,
        "calif_rate": calif_rate,
        "close_rate": close_rate,
        "ticket_promedio": ticket_prom,
    }
