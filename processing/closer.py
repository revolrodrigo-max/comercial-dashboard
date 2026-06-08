import re
import pandas as pd

# Columnas principales del tracker de ventas (cols 0-15)
CLOSER_COLS = {
    "Fecha":                  "fecha",
    "Triage":                 "triager",
    "Nombre Lead":            "lead",
    "Celular":                "celular",
    "Mail":                   "email",
    "Velocidad de contacto":  "vel_contacto",
    "Closer":                 "closer",
    "Asiste?":                "asistencia",
    "Estado del seguimiento": "estado_seguimiento",
    "Cualifica?":             "califica",
    "Compra?":                "compra",
    "Notas":                  "notas",
    "Monto Abonado (C.C)":    "cash_collected",
    "Revenue":                "revenue",
    "Medio de compra":        "medio_pago",
    "Grabacion":              "link_grabacion",
}


def _parse_money(val) -> float:
    if pd.isna(val) or str(val).strip() in ("", "-", "nan", "#DIV/0!"):
        return 0.0
    cleaned = re.sub(r"[^\d.]", "", str(val).replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _normalize_phone(phone) -> str:
    if pd.isna(phone):
        return ""
    digits = re.sub(r"\D", "", str(phone))
    return digits[-10:] if len(digits) >= 10 else digits


def process_closer(df_raw: pd.DataFrame) -> pd.DataFrame:
    if df_raw.empty:
        return pd.DataFrame()

    # Keep only the main data columns (drop summary columns on the right)
    main_cols = [c for c in CLOSER_COLS.keys() if c in df_raw.columns]
    df = df_raw[main_cols].copy()
    df = df.rename(columns=CLOSER_COLS)

    # Drop empty / header rows
    df = df[df["lead"].notna() & (df["lead"].str.strip() != "")]
    df = df[~df["lead"].isin(["Nombre Lead", "TOTAL", ""])]

    # Parse date
    df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True, errors="coerce")
    df = df[df["fecha"].notna()]

    # Parse money
    df["cash_collected"] = df["cash_collected"].apply(_parse_money)
    df["revenue"] = df["revenue"].apply(_parse_money)

    # Boolean flags
    df["asistio"] = df["asistencia"].str.strip().str.lower().isin({"asiste", "asistio", "asistió"})
    df["califico"] = df["califica"].str.strip().str.lower() == "califica"
    df["compro"] = df["compra"].str.strip().str.lower() == "compra"

    # Join keys
    df["phone_key"] = df["celular"].apply(_normalize_phone)
    df["email_key"] = df["email"].fillna("").str.lower().str.strip()

    # Time helpers
    df["mes"] = df["fecha"].dt.to_period("M").astype(str)
    df["semana"] = df["fecha"].dt.to_period("W").astype(str)
    df["dia_semana"] = df["fecha"].dt.day_name()

    return df.reset_index(drop=True)
