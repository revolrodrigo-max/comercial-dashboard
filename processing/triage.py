import re
import pandas as pd


TRIAGE_MAIN_COLS = [
    "fecha_agenda", "lead", "mail", "telefono", "ocupacion",
    "confirmacion", "asistencia", "cualifica", "va_a_closing",
    "seguimiento", "venta", "ticket", "cash_collected", "notas", "closer_triage",
]


def _parse_money(val) -> float:
    if pd.isna(val) or str(val).strip() in ("", "-", "nan", "#REF!"):
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


def process_triage(df_raw: pd.DataFrame) -> pd.DataFrame:
    if df_raw.empty:
        return pd.DataFrame()

    # Keep only the 15 main data columns
    ncols = min(15, len(df_raw.columns))
    df = df_raw.iloc[:, :ncols].copy()
    df.columns = TRIAGE_MAIN_COLS[:ncols]

    # Drop header-like rows and empty rows
    df = df[df["lead"].notna()]
    df = df[~df["lead"].isin(["Lead", "LEAD", ""])]
    df = df[~df["fecha_agenda"].isin(["Fecha de Agenda", "FECHA", ""])]

    # Parse date
    df["fecha_agenda"] = pd.to_datetime(
        df["fecha_agenda"], dayfirst=False, errors="coerce"
    )
    df = df[df["fecha_agenda"].notna()]

    # Parse money
    df["ticket"] = df["ticket"].apply(_parse_money)
    df["cash_collected"] = df["cash_collected"].apply(_parse_money)

    # Boolean funnel flags
    df["asistio"] = df["asistencia"].str.strip().str.lower() == "asiste"
    df["califico"] = df["cualifica"].str.strip().str.lower() == "cualifica"
    df["fue_a_closing"] = df["va_a_closing"].str.strip().str.lower() == "si"
    df["vendio"] = df["venta"].str.strip().str.lower() == "si"

    # Join keys
    df["phone_key"] = df["telefono"].apply(_normalize_phone)
    df["email_key"] = df["mail"].fillna("").str.lower().str.strip()

    # Month / week helpers
    df["mes"] = df["fecha_agenda"].dt.to_period("M").astype(str)
    df["semana"] = df["fecha_agenda"].dt.to_period("W").astype(str)
    df["dia_semana"] = df["fecha_agenda"].dt.day_name()

    return df.reset_index(drop=True)
