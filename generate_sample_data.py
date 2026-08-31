"""
generate_sample_data.py
========================
Generates a fully synthetic, multi-sheet procurement workbook that mimics a
real ERP/SAP export. NO real data or templates from any employer are used —
every value here is fabricated.

Run:
    python generate_sample_data.py            # -> data/sample_procurement_2026.xlsx
    python generate_sample_data.py --rows 8000 --out data/other.xlsx

The output workbook has 6 sheets:
    1. Satın Almalar        (transactions / fact table)
    2. Tedarikçiler         (supplier master)
    3. Sorumlular & Limitler(buyer master + approval limits + purchase type)
    4. Ödeme Yöntemleri     (payment method master)
    5. Kur Tablosu          (daily FX rates to TRY)
    6. Bütçe                (monthly budget per purchase type)

The generator is SEEDED, so the committed sample is reproducible.
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
SEED = 42
START = date(2025, 9, 1)      # trailing 12 months, ending "today" (2026-08-31)
END = date(2026, 8, 31)
DEFAULT_ROWS = 9000

PURCHASE_TYPES = [
    "Elektronik Satın Alma",
    "Mekanik Satın Alma",
    "Fason Satın Alma",
    "İç Satın Alma",
    "Kurumsal Satın Alma",
]

# Category pools per purchase type (keeps material descriptions plausible)
CATEGORIES = {
    "Elektronik Satın Alma": ["Elektronik", "Kablaj", "Sensör"],
    "Mekanik Satın Alma": ["Mekanik", "Hammadde", "Bağlantı Elemanı"],
    "Fason Satın Alma": ["Fason İşçilik", "Kaplama", "Talaşlı İmalat"],
    "İç Satın Alma": ["Sarf Malzeme", "Ofis", "Bakım-Onarım"],
    "Kurumsal Satın Alma": ["Hizmet", "Danışmanlık", "Yazılım Lisansı"],
}

MATERIALS = {
    "Elektronik": ["FPGA modülü", "Güç kaynağı kartı", "Konnektör seti"],
    "Kablaj": ["Blendajlı kablo", "Harness montaj seti", "RF kablo"],
    "Sensör": ["IMU sensörü", "Basınç sensörü", "Sıcaklık sensörü"],
    "Mekanik": ["Alüminyum plaka 6061", "Titanyum blok", "Rulman"],
    "Hammadde": ["Çelik levha", "Alüminyum profil", "Kompozit tabaka"],
    "Bağlantı Elemanı": ["Cıvata seti M6", "Perçin paketi", "Somun seti"],
    "Fason İşçilik": ["CNC işleme hizmeti", "Kaynak fason", "Montaj fason"],
    "Kaplama": ["Anodizasyon", "Boya kaplama", "Galvaniz"],
    "Talaşlı İmalat": ["Freze parçası", "Torna parçası", "Taşlama"],
    "Sarf Malzeme": ["Kesici takım", "Yağlayıcı", "Zımpara"],
    "Ofis": ["Kırtasiye", "Toner", "Mobilya"],
    "Bakım-Onarım": ["Yedek parça", "Filtre", "Conta"],
    "Hizmet": ["Kalibrasyon hizmeti", "Test hizmeti", "Nakliye"],
    "Danışmanlık": ["Mühendislik danışmanlığı", "Kalite danışmanlığı"],
    "Yazılım Lisansı": ["CAD lisansı", "PLM lisansı", "Analiz yazılımı"],
}

UNITS = {
    "adet": (1, 500),
    "kg": (5, 2000),
    "metre": (10, 1000),
    "saat": (8, 400),
    "paket": (1, 100),
}

# Domestic and foreign supplier name fragments (all fictional)
TR_SUFFIX = ["Savunma A.Ş.", "Mühendislik Ltd.", "Metal San.", "Teknoloji A.Ş.",
             "Elektronik Ltd.", "Makina San.", "Kompozit A.Ş.", "Sistem Ltd."]
TR_PREFIX = ["Anadolu", "Ege", "Marmara", "Toros", "Bosphorus", "Selçuk",
             "Karadeniz", "Fırat", "Meriç", "Truva", "Pınar", "Doğu"]
FR_PREFIX = ["Nord", "Vertex", "Rhein", "Atlas", "Falcon", "Orion", "Delta",
             "Precision", "Apex", "Nova"]
FR_SUFFIX = {
    "Almanya": "GmbH", "Fransa": "SAS", "ABD": "Inc.", "İngiltere": "Ltd.",
    "İtalya": "S.p.A.", "İsviçre": "AG",
}
FOREIGN_COUNTRIES = list(FR_SUFFIX.keys())
FOREIGN_CURRENCY = {  # what currency this country typically invoices in
    "Almanya": "EUR", "Fransa": "EUR", "İtalya": "EUR", "İsviçre": "EUR",
    "ABD": "USD", "İngiltere": "USD",
}

PAYMENT_METHODS = [
    ("PM01", "Peşin", 0),
    ("PM02", "Vadeli 30 Gün", 30),
    ("PM03", "Vadeli 60 Gün", 60),
    ("PM04", "Vadeli 90 Gün", 90),
    ("PM05", "Akreditif (LC)", 45),
    ("PM06", "Banka Havalesi", 15),
    ("PM07", "Çek", 30),
]

SEGMENTS = ["Stratejik", "Onaylı", "Yeni"]
DEPARTMENTS = ["Ar-Ge", "Üretim", "Kalite", "Bakım", "Proje Ofisi", "Idari İşler"]
STATUSES = ["Kapalı", "Açık", "İptal"]


# --------------------------------------------------------------------------- #
# Master-data builders
# --------------------------------------------------------------------------- #
def build_buyers(rng: np.random.Generator) -> pd.DataFrame:
    """~14 buyers, each bound to one purchase type, with an approval limit."""
    first = ["Ahmet", "Zeynep", "Mehmet", "Elif", "Can", "Deniz", "Burak",
             "Selin", "Emre", "Gizem", "Ozan", "Merve", "Kaan", "Ece"]
    last = ["Yılmaz", "Demir", "Kaya", "Şahin", "Çelik", "Aydın", "Öztürk",
            "Arslan", "Doğan", "Kılıç", "Aksoy", "Taş", "Polat", "Bulut"]
    rows = []
    for i in range(14):
        ptype = PURCHASE_TYPES[i % len(PURCHASE_TYPES)]
        limit = int(rng.choice([150_000, 300_000, 500_000, 750_000]))
        rows.append({
            "Sorumlu Kodu": f"BUY-{i+1:03d}",
            "Ad Soyad": f"{first[i]} {last[i]}",
            "Departman": rng.choice(DEPARTMENTS),
            "Satın Alma Türü": ptype,
            "Onay Limiti (TRY)": limit,
        })
    return pd.DataFrame(rows)


def build_suppliers(rng: np.random.Generator, n: int = 45) -> pd.DataFrame:
    """~45 suppliers, ~60% domestic / ~40% foreign."""
    rows = []
    for i in range(n):
        is_domestic = rng.random() < 0.60
        if is_domestic:
            name = f"{rng.choice(TR_PREFIX)} {rng.choice(TR_SUFFIX)}"
            country, origin = "Türkiye", "Yurt İçi"
        else:
            country = rng.choice(FOREIGN_COUNTRIES)
            name = f"{rng.choice(FR_PREFIX)} {FR_SUFFIX[country]}"
            origin = "Yurt Dışı"
        rows.append({
            "Tedarikçi Kodu": f"SUP-{i+1:04d}",
            "Tedarikçi Adı": name,
            "Ülke": country,
            "Menşei": origin,
            "Varsayılan Ödeme Vadesi": int(rng.choice([0, 30, 60, 90])),
            "Tedarikçi Segmenti": rng.choice(SEGMENTS, p=[0.2, 0.6, 0.2]),
        })
    return pd.DataFrame(rows)


def build_payment_methods() -> pd.DataFrame:
    return pd.DataFrame(
        [{"Ödeme Yöntemi Kodu": c, "Yöntem": m, "Vade (gün)": v}
         for c, m, v in PAYMENT_METHODS]
    )


def build_fx(rng: np.random.Generator) -> pd.DataFrame:
    """Daily USD & EUR rates to TRY via a gentle random walk. TRY = 1.0."""
    days = (END - START).days + 1
    dates = [START + timedelta(days=d) for d in range(days)]
    usd = 40.0
    eur = 44.0
    rows = []
    for d in dates:
        usd *= 1 + rng.normal(0.0006, 0.004)   # slight upward drift
        eur *= 1 + rng.normal(0.0005, 0.004)
        rows.append({"Tarih": d, "Para Birimi": "TRY", "TRY Kuru": 1.0})
        rows.append({"Tarih": d, "Para Birimi": "USD",
                     "TRY Kuru": round(usd, 4)})
        rows.append({"Tarih": d, "Para Birimi": "EUR",
                     "TRY Kuru": round(eur, 4)})
    return pd.DataFrame(rows)


def build_budget(rng: np.random.Generator) -> pd.DataFrame:
    """Monthly budget per purchase type across the date range."""
    months = pd.period_range(START, END, freq="M")
    rows = []
    base = {pt: rng.uniform(6_000_000, 14_000_000) for pt in PURCHASE_TYPES}
    for m in months:
        for pt in PURCHASE_TYPES:
            budget = base[pt] * rng.uniform(0.9, 1.15)
            rows.append({
                "Dönem (Ay)": m.strftime("%Y-%m"),
                "Satın Alma Türü": pt,
                "Bütçe (TRY)": round(budget, -3),
            })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Transaction builder
# --------------------------------------------------------------------------- #
def build_transactions(rng, buyers, suppliers, fx, n_rows) -> pd.DataFrame:
    fx_lookup = {(r["Tarih"], r["Para Birimi"]): r["TRY Kuru"]
                 for _, r in fx.iterrows()}

    buyer_recs = buyers.to_dict("records")
    dom_suppliers = suppliers[suppliers["Menşei"] == "Yurt İçi"].to_dict("records")
    for_suppliers = suppliers[suppliers["Menşei"] == "Yurt Dışı"].to_dict("records")
    pay_codes = [pm[0] for pm in PAYMENT_METHODS]

    total_days = (END - START).days
    rows = []
    po_counter = 0
    pr_counter = 0
    row_i = 0

    while row_i < n_rows:
        # ---- one purchase order (PO) = 1..4 line items ------------------- #
        po_counter += 1
        pr_counter += 1
        buyer = buyer_recs[rng.integers(len(buyer_recs))]
        ptype = buyer["Satın Alma Türü"]

        # foreign share depends a bit on purchase type
        foreign_bias = 0.45 if ptype in ("Elektronik Satın Alma",
                                          "Mekanik Satın Alma") else 0.20
        if rng.random() < foreign_bias and for_suppliers:
            supplier = for_suppliers[rng.integers(len(for_suppliers))]
            currency = FOREIGN_CURRENCY[supplier["Ülke"]]
        else:
            supplier = dom_suppliers[rng.integers(len(dom_suppliers))]
            currency = "TRY"

        # keep request & order dates within [START, END] so every order date
        # has an FX rate and no order is dated in the "future"
        req_offset = int(rng.integers(0, total_days - 20))
        req_date = START + timedelta(days=req_offset)
        order_date = req_date + timedelta(days=int(rng.integers(1, 16)))
        if order_date > END:
            order_date = END
        planned = order_date + timedelta(days=int(rng.integers(10, 61)))

        status = rng.choice(STATUSES, p=[0.7, 0.25, 0.05])
        # actual delivery only for closed & already-due orders
        actual = ""
        if status == "Kapalı" and planned <= END:
            drift = int(rng.integers(-6, 5))  # mostly on-time, some late
            actual = planned + timedelta(days=drift)

        pay_code = rng.choice(pay_codes)
        urgency = rng.choice(["Normal", "Acil"], p=[0.85, 0.15])

        n_lines = int(rng.integers(1, 5))
        for line in range(1, n_lines + 1):
            if row_i >= n_rows:
                break
            row_i += 1
            category = rng.choice(CATEGORIES[ptype])
            material = rng.choice(MATERIALS[category])
            unit = rng.choice(list(UNITS.keys()))
            lo, hi = UNITS[unit]
            qty = int(rng.integers(lo, hi))

            # Draw a target line total in TRY from a lognormal (median ~180k,
            # long right tail). This yields a realistic ~65/35 split of
            # "Limit İçi" vs "Yönetim Onayı" against the buyer limits.
            rate = fx_lookup.get((order_date, currency), 1.0)
            amount_try = min(float(rng.lognormal(mean=12.1, sigma=1.05)),
                             8_000_000.0)
            amount = round(amount_try / rate, 2)              # in currency
            unit_price = round(max(amount / qty, 0.5), 2)
            amount = round(unit_price * qty, 2)               # keep consistent
            amount_try = amount * rate

            # list price >= unit price sometimes (=> negotiated savings)
            if rng.random() < 0.55:
                list_price = round(unit_price * rng.uniform(1.02, 1.25), 2)
            else:
                list_price = unit_price

            approval = ("Yönetim Onayı"
                        if amount_try > buyer["Onay Limiti (TRY)"]
                        else "Limit İçi")

            rows.append({
                "PR No": f"PR-2026-{pr_counter:05d}",
                "PO No": f"PO-2026-{po_counter:05d}",
                "Kalem No": line,
                "Talep Tarihi": req_date,
                "Sipariş Tarihi": order_date,
                "Teslim Tarihi (Planlanan)": planned,
                "Gerçekleşen Teslim Tarihi": actual,
                "Departman": buyer["Departman"],
                "Sorumlu Kodu": buyer["Sorumlu Kodu"],
                "Tedarikçi Kodu": supplier["Tedarikçi Kodu"],
                "Kategori": category,
                "Malzeme Açıklaması": material,
                "Miktar": qty,
                "Birim": unit,
                "Birim Fiyat": unit_price,
                "Liste Fiyatı": list_price,
                "Tutar": amount,
                "Para Birimi": currency,
                "Ödeme Yöntemi Kodu": pay_code,
                "Onay Tipi": approval,
                "Durum": status,
                "Aciliyet": urgency,
            })

    df = pd.DataFrame(rows)
    return df.sort_values("Sipariş Tarihi").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic procurement workbook")
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS,
                        help="approximate number of transaction line items")
    parser.add_argument("--out", type=str,
                        default="data/sample_procurement_2026.xlsx",
                        help="output .xlsx path")
    args = parser.parse_args()

    rng = np.random.default_rng(SEED)

    buyers = build_buyers(rng)
    suppliers = build_suppliers(rng)
    payments = build_payment_methods()
    fx = build_fx(rng)
    budget = build_budget(rng)
    tx = build_transactions(rng, buyers, suppliers, fx, args.rows)

    import os
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with pd.ExcelWriter(args.out, engine="openpyxl") as xl:
        tx.to_excel(xl, sheet_name="Satın Almalar", index=False)
        suppliers.to_excel(xl, sheet_name="Tedarikçiler", index=False)
        buyers.to_excel(xl, sheet_name="Sorumlular & Limitler", index=False)
        payments.to_excel(xl, sheet_name="Ödeme Yöntemleri", index=False)
        fx.to_excel(xl, sheet_name="Kur Tablosu", index=False)
        budget.to_excel(xl, sheet_name="Bütçe", index=False)

    print(f"✓ Wrote {args.out}")
    print(f"  Transactions : {len(tx):,} line items across "
          f"{tx['PO No'].nunique():,} POs")
    print(f"  Date range   : {tx['Sipariş Tarihi'].min()} → {tx['Sipariş Tarihi'].max()}")
    print(f"  Suppliers    : {len(suppliers)}  |  Buyers: {len(buyers)}  |  "
          f"Budget rows: {len(budget)}  |  FX rows: {len(fx)}")


if __name__ == "__main__":
    main()
