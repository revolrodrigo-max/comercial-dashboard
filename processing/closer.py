import re
import pandas as pd


CLOSER_COLS = {
    "FECHA": "fecha",
    "TRIAGGE": "triager",
    "NOMBRE LEAD": "lead",
    "CELULAR": "celular",
    "EMAIL": "email",
    "VELOCIDAD DE CONTC": "vel_contacto",
    "CLOSER": "closer",
    "Estado del seguimiento": "estado_seguimiento",
    "Asiste?": "asistencia",
    "Motivo Cancelación": "motivo_cancelacion",
    "Califica?": "califica",
    "Compra?": "compra",
    "Pago": "tipo_pago",
    "Notas": "notas",
    "Cash Collected": "cash_collected",
    "Revenue": "revenue",
    "Medio de Pago": "medio_pago",
    "Link - Grabacion": "link_grabacion",
    "Documento para ONB/Servicio": "doc_onb",
}


def _parse_money(val) -> float:
    if pd.isna(val) or str(val).strip() in ("", "-", "nan"):
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

    df = df_raw.copy()

    # Rename columns that exist
    rename_map = {k: v for k, v in CLOSER_COLS.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    # Drop empty rows
    df = df[df["lead"].notna() & (df["lead"].str.strip() != "")]

    # Parse date
    df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True, errors="coerce")
    df = df[df["fecha"].notna()]

    # Parse money
    df["cash_collected"] = df["cash_collected"].apply(_parse_money)
    df["revenue"] = df["revenue"].apply(_parse_money)

    # Boolean flags
    asistencia_positiva = {"asiste", "asistio", "asistió"}
    df["asistio"] = df["asistencia"].str.strip().str.lower().isin(asistencia_positiva)
    df["califico"] = df["califica"].str.strip().str.lower() == "califica"
    df["compro"] = df["compra"].str.strip().str.lower() == "compra"
    df["es_retroactivo"] = df["tipo_pago"].str.strip().str.lower() == "retroactivo"
    df["es_upsell"] = df["tipo_pago"].str.strip().str.lower() == "upsell"

    # Join keys
    df["phone_key"] = df["celular"].apply(_normalize_phone)
    df["email_key"] = df["email"].fillna("").str.lower().str.strip()

    # Time helpers
    df["mes"] = df["fecha"].dt.to_period("M").astype(str)
    df["semana"] = df["fecha"].dt.to_period("W").astype(str)
    df["dia_semana"] = df["fecha"].dt.day_name()

    return df.reset_index(drop=True)
