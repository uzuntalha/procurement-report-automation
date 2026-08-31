"""Core-logic tests: business rules, FX conversion, validation, deck build."""

from datetime import date

import pandas as pd
import pytest

from report_generator import (
    build_dataset, week_options, compute_report_model, build_deck,
    load_workbook, ValidationError,
)


def _minimal_data():
    """A tiny but schema-complete in-memory workbook."""
    d = pd.Timestamp("2026-03-04")
    tx = pd.DataFrame([
        # within limit (100 < 250k)
        dict(**_row("PO-1", d, "BUY-1", "SUP-1", 100, 1, "TRY")),
        # over limit (400k > 250k) -> Management Approval
        dict(**_row("PO-2", d, "BUY-1", "SUP-1", 400_000, 1, "TRY")),
        # foreign USD, rate 40 -> 200k TRY (< 250k) within limit
        dict(**_row("PO-3", d, "BUY-1", "SUP-2", 5_000, 1, "USD")),
    ])
    buyers = pd.DataFrame([
        dict(**{"Sorumlu Kodu": "BUY-1", "Ad Soyad": "Ada L.",
                "Departman": "Ar-Ge", "Satın Alma Türü": "Elektronik Satın Alma",
                "Onay Limiti (TRY)": 250_000}),
    ])
    suppliers = pd.DataFrame([
        {"Tedarikçi Kodu": "SUP-1", "Tedarikçi Adı": "Local Ltd.",
         "Ülke": "Türkiye", "Menşei": "Yurt İçi",
         "Varsayılan Ödeme Vadesi": 30, "Tedarikçi Segmenti": "Onaylı"},
        {"Tedarikçi Kodu": "SUP-2", "Tedarikçi Adı": "Nord GmbH",
         "Ülke": "Almanya", "Menşei": "Yurt Dışı",
         "Varsayılan Ödeme Vadesi": 60, "Tedarikçi Segmenti": "Yeni"},
    ])
    payments = pd.DataFrame([{"Ödeme Yöntemi Kodu": "PM01", "Yöntem": "Peşin",
                              "Vade (gün)": 0}])
    fx = pd.DataFrame([
        {"Tarih": d, "Para Birimi": "TRY", "TRY Kuru": 1.0},
        {"Tarih": d, "Para Birimi": "USD", "TRY Kuru": 40.0},
    ])
    budget = pd.DataFrame([{"Dönem (Ay)": "2026-03",
                            "Satın Alma Türü": "Elektronik Satın Alma",
                            "Bütçe (TRY)": 1_000_000}])
    return {"Satın Almalar": tx, "Tedarikçiler": suppliers,
            "Sorumlular & Limitler": buyers, "Ödeme Yöntemleri": payments,
            "Kur Tablosu": fx, "Bütçe": budget}


def _row(po, d, buyer, sup, unit_price, qty, cur):
    return {
        "PO No": po, "Talep Tarihi": d - pd.Timedelta(days=3),
        "Sipariş Tarihi": d, "Teslim Tarihi (Planlanan)": d + pd.Timedelta(days=20),
        "Gerçekleşen Teslim Tarihi": pd.NaT, "Sorumlu Kodu": buyer,
        "Tedarikçi Kodu": sup, "Kategori": "Elektronik",
        "Miktar": qty, "Birim Fiyat": unit_price,
        "Liste Fiyatı": unit_price * 1.10, "Tutar": unit_price * qty,
        "Para Birimi": cur, "Ödeme Yöntemi Kodu": "PM01",
        "Onay Tipi": "Limit İçi", "Sözleşme Kapsamı": "Sözleşmeli",
        "Durum": "Açık", "Aciliyet": "Normal", "Kusurlu Teslim": "Hayır",
    }


def test_approval_type_derived_from_limit():
    ds = build_dataset(_minimal_data())
    tx = ds["tx"].set_index("PO No")
    assert tx.loc["PO-1", "Onay Tipi"] == "Limit İçi"
    assert tx.loc["PO-2", "Onay Tipi"] == "Yönetim Onayı"
    assert tx.loc["PO-3", "Onay Tipi"] == "Limit İçi"  # 5000*40 = 200k < 250k


def test_fx_conversion_to_try():
    ds = build_dataset(_minimal_data())
    tx = ds["tx"].set_index("PO No")
    assert tx.loc["PO-3", "Tutar (TRY)"] == pytest.approx(200_000.0)
    assert tx.loc["PO-1", "Tutar (TRY)"] == pytest.approx(100.0)


def test_savings_non_negative_and_scaled():
    ds = build_dataset(_minimal_data())
    tx = ds["tx"].set_index("PO No")
    # (list-unit)*qty*rate = (0.10*5000)*1*40 = 20000
    assert tx.loc["PO-3", "Tasarruf (TRY)"] == pytest.approx(20_000.0)
    assert (tx["Tasarruf (TRY)"] >= 0).all()


def test_report_model_shares():
    ds = build_dataset(_minimal_data())
    m = compute_report_model(ds, date(2026, 3, 2), date(2026, 3, 8))
    assert m["has_data"]
    # foreign spend = 200k of total (100 + 400000 + 200000) => ~0.333
    assert m["kpis"]["foreign"]["value"] == pytest.approx(200_000 / 600_100, rel=1e-3)


def test_validation_missing_column(tmp_path):
    data = _minimal_data()
    bad = data["Satın Almalar"].drop(columns=["Tutar"])
    path = tmp_path / "bad.xlsx"
    with pd.ExcelWriter(path) as xl:
        bad.to_excel(xl, sheet_name="Satın Almalar", index=False)
        for name in ["Tedarikçiler", "Sorumlular & Limitler",
                     "Ödeme Yöntemleri", "Kur Tablosu", "Bütçe"]:
            data[name].to_excel(xl, sheet_name=name, index=False)
    with pytest.raises(ValidationError) as exc:
        load_workbook(str(path))
    assert "Tutar" in str(exc.value)


def test_sample_workbook_end_to_end():
    ds = build_dataset(load_workbook("data/sample_procurement_2026.xlsx"))
    opts = week_options(ds)
    assert len(opts) >= 40
    m = compute_report_model(ds, opts[20]["start"], opts[20]["end"])
    assert m["has_data"]
    en = build_deck(m, lang="en", generated_on=date(2026, 8, 31))
    tr = build_deck(m, lang="tr", generated_on=date(2026, 8, 31))
    assert len(en) > 50_000 and len(tr) > 50_000
    assert en != tr  # bilingual output really differs
