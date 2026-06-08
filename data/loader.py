"""
Multi-sheet loader.

Both Google Sheets (ventas + triage) contain one tab PER MONTH plus a few
special tabs (objetivos, señas, archive, retroactivos). This module:

  1. Discovers every tab (gid) via the public htmlview.
  2. Reads each tab, auto-detecting the header row.
  3. Normalizes the two historical column formats to one canonical schema.
  4. Concatenates everything and de-duplicates overlapping rows.

Result is cached for CACHE_TTL seconds.
"""

import io
import re
import unicodedata
import urllib.request

import pandas as pd
import streamlit as st

from config import TRIAGE_SHEET_ID, CLOSER_SHEET_ID

CACHE_TTL = 300  # seconds
_UA = {"User-Agent": "Mozilla/5.0"}


# ── helpers ───────────────────────────────────────────────────────────────────
def _norm(text) -> str:
    """lowercase, strip accents/punctuation for fuzzy header matching."""
    if text is None:
        return ""
    s = unicodedata.normalize("NFKD", str(text))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _discover_gids(sheet_id: str) -> list[str]:
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/htmlview"
    req = urllib.request.Request(url, headers=_UA)
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    seen, out = set(), []
    for g in re.findall(r"gid=(\d+)", html):
        if g not in seen:
            seen.add(g)
            out.append(g)
    return out


def _read_gid(sheet_id: str, gid: str) -> pd.DataFrame:
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    req = urllib.request.Request(url, headers=_UA)
    raw = urllib.request.urlopen(req, timeout=30).read()
    return pd.read_csv(io.BytesIO(raw), dtype=str, header=None)


# Canonical column → list of header keywords (normalized) that map to it.
# Order matters: more specific keys are checked first in _match_columns.
_CLOSER_SCHEMA = [
    ("fecha",              ["fecha de agenda", "fecha"]),
    ("triager",            ["triagge", "triage"]),
    ("lead",               ["nombre lead", "lead"]),
    ("celular",            ["celular", "telefono"]),
    ("email",              ["email", "mail"]),
    ("vel_contacto",       ["velocidad de contc", "velocidad de contacto"]),
    ("closer",             ["closer"]),
    ("estado_seguimiento", ["estado del seguimiento", "estado de seguimiento"]),
    ("asistencia",         ["asiste"]),
    ("motivo_cancelacion", ["motivo cancelacion"]),
    ("califica",           ["califica", "cualifica"]),
    ("medio_pago",         ["medio de compra", "medio de pago"]),
    ("compra",             ["compra"]),
    ("tipo_pago",          ["pago"]),
    ("cash_collected",     ["cash collected", "monto abonado"]),
    ("revenue",            ["revenue"]),
    ("link_grabacion",     ["grabacion", "link grabacion"]),
    ("notas",              ["notas"]),
]

_TRIAGE_SCHEMA = [
    ("fecha_agenda",  ["fecha de agenda", "fecha"]),
    ("lead",          ["lead"]),
    ("mail",          ["mail", "email"]),
    ("telefono",      ["telefono", "celular"]),
    ("ocupacion",     ["ocupacion"]),
    ("confirmacion",  ["confirmacion"]),
    ("asistencia",    ["asistencia"]),
    ("cualifica",     ["cualifica", "califica"]),
    ("va_a_closing",  ["closing"]),
    ("seguimiento",   ["seguimiento"]),
    ("venta",         ["venta"]),
    ("ticket",        ["ticket"]),
    ("cash_collected",["cash collected"]),
    ("notas",         ["notes", "notas"]),
    ("closer_triage", ["closer"]),
]


def _match_columns(header_cells, schema) -> dict[int, str]:
    """Map raw column index → canonical name using keyword schema."""
    normed = [_norm(c) for c in header_cells]
    used_targets, used_idx, mapping = set(), set(), {}
    for target, keywords in schema:
        if target in used_targets:
            continue
        for kw in keywords:
            found = None
            # exact first, then contains
            for i, h in enumerate(normed):
                if i in used_idx:
                    continue
                if h == kw:
                    found = i
                    break
            if found is None:
                for i, h in enumerate(normed):
                    if i in used_idx:
                        continue
                    if kw and kw in h:
                        found = i
                        break
            if found is not None:
                mapping[found] = target
                used_idx.add(found)
                used_targets.add(target)
                break
    return mapping


def _find_header_row(df_raw: pd.DataFrame, must_have) -> int | None:
    """Scan the first few rows for one that contains all 'must_have' keywords."""
    for r in range(min(4, len(df_raw))):
        cells = [_norm(x) for x in df_raw.iloc[r].tolist()]
        if all(any(kw in c for c in cells) for kw in must_have):
            return r
    return None


def _looks_like_dates(series: pd.Series) -> bool:
    """True if a decent share of the column parses to dates in 2024-2027."""
    d = pd.to_datetime(series, errors="coerce", dayfirst=True)
    lo, hi = pd.Timestamp("2024-01-01"), pd.Timestamp("2027-12-31")
    valid = d.between(lo, hi).sum()
    return valid >= max(3, 0.3 * series.notna().sum())


def _normalize_sheet(df_raw, schema, must_have, date_target, require_any) -> pd.DataFrame | None:
    hdr = _find_header_row(df_raw, must_have)
    if hdr is None:
        return None
    header_cells = df_raw.iloc[hdr].tolist()
    mapping = _match_columns(header_cells, schema)

    if "lead" not in mapping.values():
        return None
    # Must look like a lead-tracker tab (has at least one sale-signal column),
    # so summary / señas / retroactivos / archive tabs are skipped.
    if require_any and not any(t in mapping.values() for t in require_any):
        return None

    body = df_raw.iloc[hdr + 1:].copy()

    # Fallback: date column not matched by name (e.g. header labelled "x").
    # Use the left-most unmapped column whose values parse as dates.
    if date_target not in mapping.values():
        for idx in range(len(header_cells)):
            if idx in mapping:
                continue
            if idx < body.shape[1] and _looks_like_dates(body.iloc[:, idx]):
                mapping[idx] = date_target
                break
    if date_target not in mapping.values():
        return None

    keep = {idx: name for idx, name in mapping.items() if idx < body.shape[1]}
    body = body.iloc[:, list(keep.keys())]
    body.columns = [keep[i] for i in keep.keys()]
    return body.reset_index(drop=True)


def _load_all(sheet_id, schema, must_have, dedup_keys, date_target, require_any) -> pd.DataFrame:
    frames = []
    for gid in _discover_gids(sheet_id):
        try:
            raw = _read_gid(sheet_id, gid)
            norm = _normalize_sheet(raw, schema, must_have, date_target, require_any)
            if norm is not None and not norm.empty:
                norm["_gid"] = gid
                frames.append(norm)
        except Exception:
            continue

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)

    # drop fully-empty lead rows before dedup
    lead_col = "lead"
    combined = combined[combined[lead_col].notna() & (combined[lead_col].astype(str).str.strip() != "")]

    # de-duplicate overlapping rows: keep the record with the most non-null fields
    present_keys = [k for k in dedup_keys if k in combined.columns]
    if present_keys:
        combined["_fill"] = combined.notna().sum(axis=1)
        combined["_k"] = combined[present_keys].astype(str).apply(
            lambda r: "|".join(_norm(v) for v in r), axis=1
        )
        combined = (
            combined.sort_values("_fill", ascending=False)
            .drop_duplicates("_k", keep="first")
            .drop(columns=["_fill", "_k"])
        )

    return combined.reset_index(drop=True)


# ── public API ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL, show_spinner="Cargando todas las hojas de ventas…")
def load_closer_raw() -> pd.DataFrame:
    try:
        return _load_all(
            CLOSER_SHEET_ID, _CLOSER_SCHEMA,
            must_have=["lead"],
            dedup_keys=["fecha", "lead", "celular"],
            date_target="fecha",
            require_any=["asistencia", "compra"],
        )
    except Exception as e:
        st.error(f"No se pudo cargar el tracker de ventas: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL, show_spinner="Cargando todas las hojas de triage…")
def load_triage_raw() -> pd.DataFrame:
    try:
        return _load_all(
            TRIAGE_SHEET_ID, _TRIAGE_SCHEMA,
            must_have=["lead"],
            dedup_keys=["fecha_agenda", "lead", "telefono"],
            date_target="fecha_agenda",
            require_any=["asistencia", "cualifica"],
        )
    except Exception as e:
        st.error(f"No se pudo cargar triage: {e}")
        return pd.DataFrame()


def render_upload_panel():
    """Kept for backwards-compat; multi-sheet auto-load is now the default."""
    return
