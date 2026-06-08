import re
import pandas as pd

# Canonical columns the loader produces for the ventas tracker.
EXPECTED = [
    "fecha", "triager", "lead", "celular", "email", "vel_contacto", "closer",
    "estado_seguimiento", "asistencia", "motivo_cancelacion", "califica",
    "medio_pago", "compra", "tipo_pago", "cash_collected", "revenue",
    "link_grabacion", "notas",
]

# Normalize the handful of closer-name spellings seen across the monthly tabs.
CLOSER_ALIASES = {
    "santi capurro":    "Santi Capurro",
    "santiago capurro": "Santi Capurro",
    "santi correa":     "Santi Correa",
    "santiago correa":  "Santi Correa",
    "santiago":         "Santiago",
    "santi":            "Santiago",
    "gianluca":         "Gianluca",
    "joaquin":          "Joaquin",
    "rodrigo":          "Rodrigo",
}


def _parse_money(val) -> float:
    if pd.isna(val):
        return 0.0
    s = str(val).strip()
    if s in ("", "-", "nan", "#DIV/0!", "#REF!", "#VALUE!"):
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
    """Robust against mixed D/M/Y and M/D/Y across tabs."""
    d_first = pd.to_datetime(series, errors="coerce", dayfirst=True)
    d_last = pd.to_datetime(series, errors="coerce", dayfirst=False)
    lo, hi = pd.Timestamp("2024-01-01"), pd.Timestamp("2027-12-31")
    ok_first = d_first.between(lo, hi).sum()
    ok_last = d_last.between(lo, hi).sum()
    return d_first if ok_first >= ok_last else d_last


def _canon_closer(val):
    if pd.isna(val):
        return val
    return CLOSER_ALIASES.get(str(val).strip().lower(), str(val).strip())


def process_closer(df_in: pd.DataFrame) -> pd.DataFrame:
    if df_in.empty:
        return pd.DataFrame()

    df = df_in.copy()
    for col in EXPECTED:
        if col not in df.columns:
            df[col] = pd.NA

    # Drop header echoes / totals
    df = df[df["lead"].notna() & (df["lead"].astype(str).str.strip() != "")]
    df = df[~df["lead"].astype(str).str.strip().isin(["Nombre Lead", "NOMBRE LEAD", "TOTAL", "Lead"])]

    df["fecha"] = _parse_dates(df["fecha"])
    df = df[df["fecha"].notna()]

    df["closer"] = df["closer"].apply(_canon_closer)

    df["cash_collected"] = df["cash_collected"].apply(_parse_money)
    df["revenue"] = df["revenue"].apply(_parse_money)

    df["asistio"] = df["asistencia"].astype(str).str.strip().str.lower().isin(
        {"asiste", "asistio", "asistió"}
    )
    df["califico"] = df["califica"].astype(str).str.strip().str.lower().isin(
        {"califica", "cualifica"}
    )
    df["compro"] = df["compra"].astype(str).str.strip().str.lower() == "compra"

    df["phone_key"] = df["celular"].apply(_normalize_phone)
    df["email_key"] = df["email"].fillna("").astype(str).str.lower().str.strip()

    df["mes"] = df["fecha"].dt.to_period("M").astype(str)
    df["semana"] = df["fecha"].dt.to_period("W").astype(str)
    df["dia_semana"] = df["fecha"].dt.day_name()

    return df.reset_index(drop=True)
