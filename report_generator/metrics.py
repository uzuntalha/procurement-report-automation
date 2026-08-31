"""Enrichment + aggregation: turn validated sheets into a report model.

``build_dataset`` joins the sheets, converts every line to TRY using the
date-appropriate FX rate, derives the approval type from each buyer's limit,
and computes savings / lead-time / delivery flags. ``compute_report_model``
then slices a chosen week (with previous-week and year-to-date context) and
produces every aggregation the 13 slides need.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd


# --------------------------------------------------------------------------- #
# Dataset enrichment
# --------------------------------------------------------------------------- #
def build_dataset(data: dict[str, pd.DataFrame]) -> dict:
    """Join sheets and compute derived fields. Returns an enriched context."""
    tx = data["Satın Almalar"].copy().reset_index(drop=True)

    buyers = data["Sorumlular & Limitler"]
    suppliers = data["Tedarikçiler"]
    payments = data["Ödeme Yöntemleri"]

    tx = tx.merge(
        buyers[["Sorumlu Kodu", "Ad Soyad", "Satın Alma Türü", "Onay Limiti (TRY)"]],
        on="Sorumlu Kodu", how="left")
    tx = tx.merge(
        suppliers[["Tedarikçi Kodu", "Tedarikçi Adı", "Ülke", "Menşei",
                   "Tedarikçi Segmenti"]],
        on="Tedarikçi Kodu", how="left")
    tx = tx.merge(payments[["Ödeme Yöntemi Kodu", "Yöntem", "Vade (gün)"]],
                  on="Ödeme Yöntemi Kodu", how="left")

    # --- FX -> TRY using nearest-date rate per currency -------------------- #
    tx["_date"] = tx["Sipariş Tarihi"].dt.normalize()
    tx["Kur"] = 1.0
    kur = data["Kur Tablosu"].dropna(subset=["Tarih", "TRY Kuru"]).copy()
    kur["Tarih"] = kur["Tarih"].dt.normalize()
    for cur, g in kur.groupby("Para Birimi"):
        if cur == "TRY":
            continue
        mask = tx["Para Birimi"] == cur
        if not mask.any():
            continue
        left = tx.loc[mask, ["_date"]].sort_values("_date")
        right = (g[["Tarih", "TRY Kuru"]].rename(columns={"Tarih": "_date"})
                 .sort_values("_date"))
        merged = pd.merge_asof(left, right, on="_date", direction="nearest")
        tx.loc[left.index, "Kur"] = merged["TRY Kuru"].values

    tx["Tutar (TRY)"] = tx["Tutar"] * tx["Kur"]

    # --- derived business fields ------------------------------------------ #
    # Approval type is DERIVED from the buyer's limit (business rule in code).
    tx["Onay Tipi"] = tx["Tutar (TRY)"].gt(tx["Onay Limiti (TRY)"]).map(
        {True: "Yönetim Onayı", False: "Limit İçi"})

    tx["Tasarruf (TRY)"] = (
        (tx["Liste Fiyatı"] - tx["Birim Fiyat"]).clip(lower=0)
        * tx["Miktar"] * tx["Kur"])

    tx["Lead Time"] = (tx["Sipariş Tarihi"] - tx["Talep Tarihi"]).dt.days

    if "Gerçekleşen Teslim Tarihi" in tx.columns:
        delivered = tx["Gerçekleşen Teslim Tarihi"].notna()
        tx["Zamanında"] = pd.NA
        tx.loc[delivered, "Zamanında"] = (
            tx.loc[delivered, "Gerçekleşen Teslim Tarihi"]
            <= tx.loc[delivered, "Teslim Tarihi (Planlanan)"])
    else:
        tx["Zamanında"] = pd.NA

    tx["Acil"] = tx["Aciliyet"].eq("Acil")
    tx["Kusurlu"] = tx.get("Kusurlu Teslim", "Hayır").eq("Evet")

    return {"tx": tx, "budget": data["Bütçe"]}


# --------------------------------------------------------------------------- #
# Week selection
# --------------------------------------------------------------------------- #
def week_options(dataset: dict) -> list[dict]:
    """Return selectable weeks (Mon–Sun) that actually contain data."""
    d = dataset["tx"]["_date"].dropna()
    if d.empty:
        return []
    mondays = (d - pd.to_timedelta(d.dt.weekday, unit="D")).dt.normalize()
    opts = []
    for monday in sorted(mondays.unique()):
        start = pd.Timestamp(monday).date()
        end = start + timedelta(days=6)
        iso = start.isocalendar()
        label = (f"{start:%d %b} – {end:%d %b %Y}  ·  W{iso.week:02d}")
        opts.append({"start": start, "end": end, "label": label})
    return opts


# --------------------------------------------------------------------------- #
# Report model
# --------------------------------------------------------------------------- #
def _slice(tx, start: date, end: date) -> pd.DataFrame:
    d = tx["_date"]
    return tx[(d >= pd.Timestamp(start)) & (d <= pd.Timestamp(end))]


def _spend(df) -> float:
    return float(df["Tutar (TRY)"].sum())


def _delta(cur: float, prev: float):
    """Return signed pct change vs prev, or None if prev is 0."""
    if prev in (0, None) or pd.isna(prev):
        return None
    return (cur - prev) / prev


def compute_report_model(dataset: dict, week_start: date, week_end: date) -> dict:
    """Compute every aggregation the deck needs for the selected week."""
    tx = dataset["tx"]
    budget = dataset["budget"]

    cur = _slice(tx, week_start, week_end)
    prev = _slice(tx, week_start - timedelta(days=7), week_start - timedelta(days=1))
    ytd_start = date(week_end.year, 1, 1)
    ytd = _slice(tx, ytd_start, week_end)

    model: dict = {
        "week_start": week_start,
        "week_end": week_end,
        "has_data": len(cur) > 0,
    }

    # --- KPIs -------------------------------------------------------------- #
    def share(df, col, val):
        s = _spend(df)
        return (_spend(df[df[col] == val]) / s) if s else 0.0

    otd_pool = cur[cur["Zamanında"].notna()]
    model["kpis"] = {
        "spend": {"value": _spend(cur), "delta": _delta(_spend(cur), _spend(prev))},
        "pos": {"value": int(cur["PO No"].nunique()),
                "delta": _delta(cur["PO No"].nunique(), prev["PO No"].nunique())},
        "lines": {"value": int(len(cur)), "delta": _delta(len(cur), len(prev))},
        "foreign": {"value": share(cur, "Menşei", "Yurt Dışı"), "delta": None},
        "approval": {"value": share(cur, "Onay Tipi", "Yönetim Onayı"), "delta": None},
        "savings": {"value": float(cur["Tasarruf (TRY)"].sum()),
                    "delta": _delta(cur["Tasarruf (TRY)"].sum(),
                                    prev["Tasarruf (TRY)"].sum())},
        "emergency": {"value": (cur["Acil"].mean() if len(cur) else 0.0),
                      "delta": None},
        "otd": {"value": (float(otd_pool["Zamanında"].mean())
                          if len(otd_pool) else None), "delta": None},
    }

    # --- Slide aggregations (Series/DataFrames in canonical TR labels) ------ #
    model["by_ptype"] = (cur.groupby("Satın Alma Türü")["Tutar (TRY)"]
                         .sum().sort_values(ascending=False))

    top_buyers = (cur.groupby("Ad Soyad")["Tutar (TRY)"].sum()
                  .sort_values(ascending=False).head(10).index)
    buyer_stack = (cur[cur["Ad Soyad"].isin(top_buyers)]
                   .groupby(["Ad Soyad", "Onay Tipi"])["Tutar (TRY)"].sum()
                   .unstack(fill_value=0.0))
    for c in ("Limit İçi", "Yönetim Onayı"):
        if c not in buyer_stack.columns:
            buyer_stack[c] = 0.0
    model["buyer_stack"] = buyer_stack.loc[
        buyer_stack.sum(axis=1).sort_values(ascending=False).index,
        ["Limit İçi", "Yönetim Onayı"]]

    model["approval_spend"] = cur.groupby("Onay Tipi")["Tutar (TRY)"].sum()
    model["approval_count"] = cur.groupby("Onay Tipi")["PO No"].count()

    sup = (cur.groupby("Tedarikçi Adı")["Tutar (TRY)"].sum()
           .sort_values(ascending=False))
    model["supplier_pareto"] = sup

    model["origin_spend"] = cur.groupby("Menşei")["Tutar (TRY)"].sum()
    model["country_spend"] = (cur.groupby("Ülke")["Tutar (TRY)"].sum()
                              .sort_values(ascending=False).head(8))

    model["category_spend"] = (cur.groupby("Kategori")["Tutar (TRY)"].sum()
                               .sort_values(ascending=False))
    model["payment_spend"] = (cur.groupby("Yöntem")["Tutar (TRY)"].sum()
                              .sort_values(ascending=False))

    # --- YTD weekly trend --------------------------------------------------- #
    y = ytd.copy()
    y["_wk"] = (y["_date"] - pd.to_timedelta(y["_date"].dt.weekday, unit="D")).dt.normalize()
    model["trend"] = y.groupby("_wk")["Tutar (TRY)"].sum()
    model["trend_marker"] = pd.Timestamp(week_start)

    # --- Savings waterfall (gross list-price spend -> savings -> net) ------- #
    gross = float((cur["Liste Fiyatı"] * cur["Miktar"] * cur["Kur"]).sum())
    saved = float(cur["Tasarruf (TRY)"].sum())
    model["savings_waterfall"] = {"gross": gross, "saved": saved,
                                  "net": gross - saved}
    model["savings_by_ptype"] = (cur.groupby("Satın Alma Türü")["Tasarruf (TRY)"]
                                 .sum().sort_values(ascending=False))

    # --- Budget vs actual (month-to-date of the reporting week) ------------- #
    month_key = f"{week_end.year}-{week_end.month:02d}"
    mtd = _slice(tx, date(week_end.year, week_end.month, 1), week_end)
    actual_by_type = mtd.groupby("Satın Alma Türü")["Tutar (TRY)"].sum()
    bud = budget[budget["Dönem (Ay)"] == month_key]
    budget_by_type = bud.set_index("Satın Alma Türü")["Bütçe (TRY)"]
    types = sorted(set(actual_by_type.index) | set(budget_by_type.index))
    model["budget_actual"] = pd.DataFrame({
        "Bütçe": budget_by_type.reindex(types).fillna(0.0),
        "Gerçekleşen": actual_by_type.reindex(types).fillna(0.0),
    }, index=types)
    model["budget_month"] = month_key

    # --- Risk --------------------------------------------------------------- #
    total = _spend(cur)
    model["risk"] = {
        "top_supplier_share": (sup.iloc[0] / total) if (total and len(sup)) else 0.0,
        "top5_share": (sup.head(5).sum() / total) if total else 0.0,
        "fx_share": (1 - share(cur, "Para Birimi", "TRY")) if total else 0.0,
        "hhi": float(((sup / total) ** 2).sum()) if total else 0.0,
    }

    # --- Week-over-week scorecard ------------------------------------------ #
    def mshare(df, col, val):
        s = _spend(df)
        return (_spend(df[df[col] == val]) / s) if s else 0.0

    model["wow"] = [
        ("kpi_spend", _spend(cur), _spend(prev), "try"),
        ("kpi_pos", cur["PO No"].nunique(), prev["PO No"].nunique(), "int"),
        ("kpi_savings", float(cur["Tasarruf (TRY)"].sum()),
         float(prev["Tasarruf (TRY)"].sum()), "try"),
        ("kpi_approval", mshare(cur, "Onay Tipi", "Yönetim Onayı"),
         mshare(prev, "Onay Tipi", "Yönetim Onayı"), "pct"),
        ("kpi_foreign", mshare(cur, "Menşei", "Yurt Dışı"),
         mshare(prev, "Menşei", "Yurt Dışı"), "pct"),
        ("kpi_emergency", (cur["Acil"].mean() if len(cur) else 0.0),
         (prev["Acil"].mean() if len(prev) else 0.0), "pct"),
    ]

    # spend by purchase type — this week vs last week
    prev_ptype = prev.groupby("Satın Alma Türü")["Tutar (TRY)"].sum()
    model["ptype_compare"] = pd.DataFrame({
        "cur": model["by_ptype"],
        "prev": prev_ptype.reindex(model["by_ptype"].index).fillna(0.0),
    })

    # --- Contract compliance / maverick spend / spend-under-management ------ #
    model["contract_spend"] = cur.groupby("Sözleşme Kapsamı")["Tutar (TRY)"].sum()
    on_contract = _spend(cur[cur["Sözleşme Kapsamı"] == "Sözleşmeli"])
    model["compliance"] = {
        "sum_share": (on_contract / total) if total else 0.0,       # spend under mgmt
        "maverick_share": (1 - on_contract / total) if total else 0.0,
        "maverick_benchmark": 0.10,   # best-in-class < 10%
        "sum_benchmark": 0.80,        # best-in-class > 80%
    }

    # --- Supplier scorecard (top suppliers × OTD × defect × segment) -------- #
    scols = []
    for name, g in cur.groupby("Tedarikçi Adı"):
        delivered = g[g["Zamanında"].notna()]
        scols.append({
            "supplier": name,
            "spend": _spend(g),
            "otd": (float(delivered["Zamanında"].mean()) if len(delivered) else None),
            "defect": (float(g["Kusurlu"].mean())),
            "segment": g["Tedarikçi Segmenti"].iloc[0],
        })
    sc = pd.DataFrame(scols).sort_values("spend", ascending=False).head(8)
    model["supplier_scorecard"] = sc.reset_index(drop=True)

    # --- Tail spend --------------------------------------------------------- #
    if total and len(sup):
        cum = sup.cumsum() / total
        n80 = int((cum < 0.8).sum()) + 1
        tail_count = int(len(sup) - n80)
        tail_share = float(sup.iloc[n80:].sum() / total) if n80 < len(sup) else 0.0
    else:
        n80, tail_count, tail_share = 0, 0, 0.0
    model["tail"] = {"n80": n80, "total_suppliers": int(len(sup)),
                     "tail_count": tail_count, "tail_share": tail_share}

    # --- Payment terms / DPO ------------------------------------------------ #
    if total:
        w = cur["Tutar (TRY)"]
        model["dpo"] = float((cur["Vade (gün)"] * w).sum() / w.sum())
    else:
        model["dpo"] = 0.0

    # --- Highlights & exceptions ------------------------------------------- #
    po = (cur.groupby("PO No").agg(
            amount=("Tutar (TRY)", "sum"),
            supplier=("Tedarikçi Adı", "first"),
            buyer=("Ad Soyad", "first"),
            ptype=("Satın Alma Türü", "first"),
            approval=("Onay Tipi", "first"),
            urgency=("Aciliyet", "first"),
            segment=("Tedarikçi Segmenti", "first"),
         ).sort_values("amount", ascending=False).head(6).reset_index())
    model["highlights"] = po
    model["exceptions"] = {
        "new_suppliers": int((cur["Tedarikçi Segmenti"] == "Yeni")
                             .groupby(cur["Tedarikçi Adı"]).any().sum()),
        "emergency": int(cur["Acil"].sum()),
        "mgmt_approvals": int((cur["Onay Tipi"] == "Yönetim Onayı").sum()),
    }

    return model
