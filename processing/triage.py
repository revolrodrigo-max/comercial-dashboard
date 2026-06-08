import re
import pandas as pd

EXPECTED = [
    "fecha_agenda", "lead", "mail", "telefono", "ocupacion", "confirmacion",
    "asistencia", "cualifica", "va_a_closing", "seguimiento", "venta",
    "ticket", "cash_collected", "notas", "closer_triage",
]


def _parse_money(val) -> float:
    if pd.isna(val):
        return 0.0
    s = str(val).strip()
    if s in ("", "-", "nan", "#REF!", "#DIV/0!", "#VALUE!"):
        return 0.0
    cleaned = re.sub(r"[^\d.]", "", s.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _normalize_phone(phone) -> str:
    if pd.isna(phone):
        return ""
    digits = re.sub(r"\D", "", str(phone))
    return digits[-10:] if len(digits) >= 10 else digits


def _parse_dates(series: pd.Series) -> pd.Series:
    d_first = pd.to_datetime(series, errors="coerce", dayfirst=True)
    d_last = pd.to_datetime(series, errors="coerce", dayfirst=False)
    lo, hi = pd.Timestamp("2024-01-01"), pd.Timestamp("2027-12-31")
    return d_first if d_first.between(lo, hi).sum() >= d_last.between(lo, hi).sum() else d_last


def process_triage(df_in: pd.DataFrame) -> pd.DataFrame:
    if df_in.empty:
        return pd.DataFrame()

    df = df_in.copy()
    for col in EXPECTED:
        if col not in df.columns:
            df[col] = pd.NA

    df = df[df["lead"].notna() & (df["lead"].astype(str).str.strip() != "")]
    df = df[~df["lead"].astype(str).str.strip().isin(["Lead", "LEAD"])]

    df["fecha_agenda"] = _parse_dates(df["fecha_agenda"])
    df = df[df["fecha_agenda"].notna()]

    df["ticket"] = df["ticket"].apply(_parse_money)
    df["cash_collected"] = df["cash_collected"].apply(_parse_money)

    df["asistio"] = df["asistencia"].astype(str).str.strip().str.lower() == "asiste"
    df["califico"] = df["cualifica"].astype(str).str.strip().str.lower() == "cualifica"
    df["fue_a_closing"] = df["va_a_closing"].astype(str).str.strip().str.lower() == "si"
    df["vendio"] = df["venta"].astype(str).str.strip().str.lower() == "si"

    df["phone_key"] = df["telefono"].apply(_normalize_phone)
    df["email_key"] = df["mail"].fillna("").astype(str).str.lower().str.strip()

    df["mes"] = df["fecha_agenda"].dt.to_period("M").astype(str)
    df["semana"] = df["fecha_agenda"].dt.to_period("W").astype(str)
    df["dia_semana"] = df["fecha_agenda"].dt.day_name()

    return df.reset_index(drop=True)
