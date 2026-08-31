"""Workbook loading, schema validation, and TR/EN column mapping.

The tool must accept *any* week's workbook, not one hard-coded file — so it
validates the uploaded workbook against an expected schema and raises clear,
user-friendly errors when something is missing. English sheet/column headers
are accepted too, via alias maps (no fuzzy matching).
"""

from __future__ import annotations

import pandas as pd


class ValidationError(Exception):
    """Raised when an uploaded workbook does not match the expected schema.

    The message is written to be shown directly to a non-technical user.
    """


# Canonical (Turkish) sheet names and the columns each MUST contain.
REQUIRED_COLUMNS = {
    "Satın Almalar": [
        "PO No", "Talep Tarihi", "Sipariş Tarihi", "Teslim Tarihi (Planlanan)",
        "Sorumlu Kodu", "Tedarikçi Kodu", "Kategori", "Miktar", "Birim Fiyat",
        "Liste Fiyatı", "Tutar", "Para Birimi", "Ödeme Yöntemi Kodu",
        "Onay Tipi", "Sözleşme Kapsamı", "Durum", "Aciliyet", "Kusurlu Teslim",
    ],
    "Tedarikçiler": ["Tedarikçi Kodu", "Tedarikçi Adı", "Ülke", "Menşei",
                     "Tedarikçi Segmenti"],
    "Sorumlular & Limitler": ["Sorumlu Kodu", "Ad Soyad", "Departman",
                              "Satın Alma Türü", "Onay Limiti (TRY)"],
    "Ödeme Yöntemleri": ["Ödeme Yöntemi Kodu", "Yöntem"],
    "Kur Tablosu": ["Tarih", "Para Birimi", "TRY Kuru"],
    "Bütçe": ["Dönem (Ay)", "Satın Alma Türü", "Bütçe (TRY)"],
}

# English sheet-name aliases -> canonical Turkish name.
SHEET_ALIASES = {
    "purchases": "Satın Almalar", "transactions": "Satın Almalar",
    "suppliers": "Tedarikçiler",
    "buyers": "Sorumlular & Limitler", "buyers & limits": "Sorumlular & Limitler",
    "payment methods": "Ödeme Yöntemleri",
    "fx rates": "Kur Tablosu", "exchange rates": "Kur Tablosu",
    "budget": "Bütçe",
}

# English column-header aliases -> canonical Turkish column, per sheet.
COLUMN_ALIASES = {
    "Satın Almalar": {
        "po no": "PO No", "pr no": "PR No", "line no": "Kalem No",
        "request date": "Talep Tarihi", "order date": "Sipariş Tarihi",
        "planned delivery": "Teslim Tarihi (Planlanan)",
        "actual delivery": "Gerçekleşen Teslim Tarihi",
        "department": "Departman", "buyer code": "Sorumlu Kodu",
        "supplier code": "Tedarikçi Kodu", "category": "Kategori",
        "material": "Malzeme Açıklaması", "quantity": "Miktar",
        "unit": "Birim", "unit price": "Birim Fiyat",
        "list price": "Liste Fiyatı", "amount": "Tutar",
        "currency": "Para Birimi", "payment method code": "Ödeme Yöntemi Kodu",
        "approval type": "Onay Tipi", "contract coverage": "Sözleşme Kapsamı",
        "status": "Durum", "urgency": "Aciliyet",
        "defective delivery": "Kusurlu Teslim",
    },
    "Tedarikçiler": {
        "supplier code": "Tedarikçi Kodu", "supplier name": "Tedarikçi Adı",
        "country": "Ülke", "origin": "Menşei",
        "default payment terms": "Varsayılan Ödeme Vadesi",
        "supplier segment": "Tedarikçi Segmenti",
    },
    "Sorumlular & Limitler": {
        "buyer code": "Sorumlu Kodu", "name": "Ad Soyad",
        "department": "Departman", "purchase type": "Satın Alma Türü",
        "approval limit (try)": "Onay Limiti (TRY)",
    },
    "Ödeme Yöntemleri": {
        "payment method code": "Ödeme Yöntemi Kodu", "method": "Yöntem",
        "term (days)": "Vade (gün)",
    },
    "Kur Tablosu": {"date": "Tarih", "currency": "Para Birimi",
                    "try rate": "TRY Kuru"},
    "Bütçe": {"period (month)": "Dönem (Ay)",
              "purchase type": "Satın Alma Türü", "budget (try)": "Bütçe (TRY)"},
}


def _canonical_sheet_map(found_sheets):
    """Map the workbook's actual sheet names to canonical names."""
    resolved = {}
    for name in found_sheets:
        key = name.strip()
        if key in REQUIRED_COLUMNS:
            resolved[key] = name
        elif key.lower() in SHEET_ALIASES:
            resolved[SHEET_ALIASES[key.lower()]] = name
    return resolved


def _rename_columns(df, sheet):
    """Rename English/alias headers to canonical Turkish ones."""
    aliases = COLUMN_ALIASES.get(sheet, {})
    rename = {}
    for col in df.columns:
        c = str(col).strip()
        if c in REQUIRED_COLUMNS.get(sheet, []):
            continue
        if c.lower() in aliases:
            rename[col] = aliases[c.lower()]
    return df.rename(columns=rename)


def load_workbook(source) -> dict[str, pd.DataFrame]:
    """Load and validate a procurement workbook.

    Parameters
    ----------
    source : path or file-like
        An ``.xlsx`` file (path string or an uploaded file buffer).

    Returns
    -------
    dict[str, DataFrame]
        Keyed by canonical sheet name.

    Raises
    ------
    ValidationError
        With a user-friendly message if a sheet or required column is missing.
    """
    try:
        xl = pd.ExcelFile(source, engine="openpyxl")
    except Exception as exc:  # noqa: BLE001
        raise ValidationError(
            f"Could not open the file as an Excel workbook (.xlsx). Details: {exc}"
        ) from exc

    sheet_map = _canonical_sheet_map(xl.sheet_names)

    missing_sheets = [s for s in REQUIRED_COLUMNS if s not in sheet_map]
    if missing_sheets:
        raise ValidationError(
            "The workbook is missing required sheet(s): "
            + ", ".join(f"'{s}'" for s in missing_sheets)
            + ". Expected sheets: "
            + ", ".join(f"'{s}'" for s in REQUIRED_COLUMNS)
            + "."
        )

    data = {}
    for canonical, actual in sheet_map.items():
        df = xl.parse(actual)
        df = _rename_columns(df, canonical)
        required = REQUIRED_COLUMNS[canonical]
        missing_cols = [c for c in required if c not in df.columns]
        if missing_cols:
            raise ValidationError(
                f"Sheet '{canonical}' is missing required column(s): "
                + ", ".join(f"'{c}'" for c in missing_cols)
                + f". Found columns: {', '.join(map(str, df.columns))}."
            )
        data[canonical] = df

    _coerce_types(data)
    return data


def _coerce_types(data: dict[str, pd.DataFrame]) -> None:
    """Best-effort type coercion for dates and numerics, with clear errors."""
    tx = data["Satın Almalar"]
    for col in ["Talep Tarihi", "Sipariş Tarihi", "Teslim Tarihi (Planlanan)",
                "Gerçekleşen Teslim Tarihi"]:
        if col in tx.columns:
            tx[col] = pd.to_datetime(tx[col], errors="coerce")
    for col in ["Miktar", "Birim Fiyat", "Liste Fiyatı", "Tutar"]:
        tx[col] = pd.to_numeric(tx[col], errors="coerce")
    if tx["Sipariş Tarihi"].isna().all():
        raise ValidationError(
            "Column 'Sipariş Tarihi' in 'Satın Almalar' has no valid dates."
        )

    data["Kur Tablosu"]["Tarih"] = pd.to_datetime(
        data["Kur Tablosu"]["Tarih"], errors="coerce")
    data["Kur Tablosu"]["TRY Kuru"] = pd.to_numeric(
        data["Kur Tablosu"]["TRY Kuru"], errors="coerce")
    data["Sorumlular & Limitler"]["Onay Limiti (TRY)"] = pd.to_numeric(
        data["Sorumlular & Limitler"]["Onay Limiti (TRY)"], errors="coerce")
    data["Bütçe"]["Bütçe (TRY)"] = pd.to_numeric(
        data["Bütçe"]["Bütçe (TRY)"], errors="coerce")
