"""Bilingual (EN/TR) label + categorical-value dictionaries.

The whole pipeline keeps data in canonical Turkish column/value names
(matching the source workbook). Only *display* strings — slide titles, KPI
labels, axis labels, and categorical values shown on charts — are translated
here, based on the selected report language.
"""

from __future__ import annotations

DEFAULT_LANG = "en"
LANGUAGES = ("en", "tr")

# --------------------------------------------------------------------------- #
# UI + slide/label strings
# --------------------------------------------------------------------------- #
_T = {
    # --- app / ui ---------------------------------------------------------- #
    "app_title": {"en": "Procurement Weekly Report Automation",
                  "tr": "Satın Alma Haftalık Rapor Otomasyonu"},
    "app_tagline": {"en": "Turn a procurement workbook into an executive deck — in one click.",
                    "tr": "Satın alma workbook'unu tek tıkla yönetici sunumuna çevirin."},
    "upload": {"en": "1 · Upload procurement workbook (.xlsx)",
               "tr": "1 · Satın alma workbook'u yükleyin (.xlsx)"},
    "use_sample": {"en": "Use the bundled sample workbook",
                   "tr": "Hazır örnek workbook'u kullan"},
    "download_template": {"en": "⬇️ Download a sample workbook (template)",
                          "tr": "⬇️ Örnek workbook indir (şablon)"},
    "uploaded_ok": {"en": "Using your uploaded workbook.",
                    "tr": "Yüklediğiniz workbook kullanılıyor."},
    "using_sample": {"en": "No file uploaded — using the bundled sample workbook. "
                           "Upload your own .xlsx above to run it on real data.",
                     "tr": "Dosya yüklenmedi — hazır örnek workbook kullanılıyor. "
                           "Kendi .xlsx dosyanızı yukarıdan yükleyerek çalıştırabilirsiniz."},
    "select_week": {"en": "2 · Select reporting week",
                    "tr": "2 · Raporlanacak haftayı seçin"},
    "report_lang": {"en": "3 · Report language",
                    "tr": "3 · Rapor dili"},
    "generate": {"en": "Generate report", "tr": "Rapor oluştur"},
    "download": {"en": "Download .pptx", "tr": ".pptx indir"},
    "ui_language": {"en": "Interface language", "tr": "Arayüz dili"},

    # --- deck-wide --------------------------------------------------------- #
    "deck_title": {"en": "Procurement Weekly Report",
                   "tr": "Satın Alma Haftalık Raporu"},
    "week_of": {"en": "Week of", "tr": "Hafta"},
    "vs_prev": {"en": "vs. previous week", "tr": "önceki haftaya göre"},
    "synthetic_note": {
        "en": "Fictional context · 100% synthetic data · no real company or template",
        "tr": "Kurgusal bağlam · %100 sentetik veri · gerçek şirket/şablon değildir"},
    "generated_on": {"en": "Generated", "tr": "Oluşturulma"},

    # --- slide titles ------------------------------------------------------ #
    "s_exec": {"en": "Executive Summary", "tr": "Yönetici Özeti"},
    "s_ptype": {"en": "Spend by Purchase Type", "tr": "Satın Alma Türüne Göre Harcama"},
    "s_buyer": {"en": "Spend by Buyer — Within-Limit vs. Management Approval",
                "tr": "Sorumluya Göre Harcama — Limit İçi vs. Yönetim Onayı"},
    "s_approval": {"en": "Approval Type Analysis", "tr": "Onay Tipi Analizi"},
    "s_supplier": {"en": "Supplier Concentration (Pareto)",
                   "tr": "Tedarikçi Yoğunlaşması (Pareto)"},
    "s_origin": {"en": "Domestic vs. Foreign Sourcing",
                 "tr": "Yurt İçi / Yurt Dışı Tedarik"},
    "s_catpay": {"en": "Category & Payment Method Breakdown",
                 "tr": "Kategori ve Ödeme Yöntemi Kırılımı"},
    "s_trend": {"en": "Weekly Spend Trend (Year-to-Date)",
                "tr": "Haftalık Harcama Trendi (Yıl Başından Bugüne)"},
    "s_savings": {"en": "Negotiated Savings", "tr": "Müzakere Tasarrufu"},
    "s_budget": {"en": "Budget vs. Actual", "tr": "Bütçe vs. Gerçekleşen"},
    "s_risk": {"en": "Risk — Supplier Concentration & FX Exposure",
               "tr": "Risk — Tedarikçi Yoğunlaşması ve Döviz Riski"},
    "s_highlights": {"en": "Highlights & Exceptions", "tr": "Dikkat Çekenler ve İstisnalar"},

    # --- KPI labels -------------------------------------------------------- #
    "kpi_spend": {"en": "Total Spend", "tr": "Toplam Harcama"},
    "kpi_pos": {"en": "Purchase Orders", "tr": "Satın Alma Siparişi"},
    "kpi_lines": {"en": "Line Items", "tr": "Sipariş Kalemi"},
    "kpi_foreign": {"en": "Foreign Share", "tr": "Yurt Dışı Payı"},
    "kpi_approval": {"en": "Mgmt-Approval Share", "tr": "Yönetim Onayı Payı"},
    "kpi_savings": {"en": "Savings", "tr": "Tasarruf"},
    "kpi_emergency": {"en": "Emergency Buys", "tr": "Acil Alım"},
    "kpi_otd": {"en": "On-Time Delivery", "tr": "Zamanında Teslim"},

    # --- misc chart labels ------------------------------------------------- #
    "spend_try": {"en": "Spend (TRY)", "tr": "Harcama (TRY)"},
    "cumulative": {"en": "Cumulative %", "tr": "Kümülatif %"},
    "within_limit": {"en": "Within Limit", "tr": "Limit İçi"},
    "mgmt_approval": {"en": "Management Approval", "tr": "Yönetim Onayı"},
    "budget": {"en": "Budget", "tr": "Bütçe"},
    "actual": {"en": "Actual", "tr": "Gerçekleşen"},
    "others": {"en": "Others", "tr": "Diğer"},
    "no_data": {"en": "No data for the selected week.",
                "tr": "Seçilen hafta için veri yok."},
    "h_top_po": {"en": "Largest orders this week", "tr": "Bu haftanın en büyük siparişleri"},
    "col_po": {"en": "PO", "tr": "PO"},
    "col_supplier": {"en": "Supplier", "tr": "Tedarikçi"},
    "col_buyer": {"en": "Buyer", "tr": "Sorumlu"},
    "col_amount": {"en": "Amount (TRY)", "tr": "Tutar (TRY)"},
    "col_type": {"en": "Type", "tr": "Tür"},
    "col_flag": {"en": "Flag", "tr": "İşaret"},
    "flag_emergency": {"en": "Emergency", "tr": "Acil"},
    "flag_new_supplier": {"en": "New supplier", "tr": "Yeni tedarikçi"},
    "flag_mgmt": {"en": "Mgmt approval", "tr": "Yönetim onayı"},
}

# --------------------------------------------------------------------------- #
# Categorical value translations (canonical TR -> EN)
# --------------------------------------------------------------------------- #
_VALUES_EN = {
    # purchase types
    "Elektronik Satın Alma": "Electronics",
    "Mekanik Satın Alma": "Mechanical",
    "Fason Satın Alma": "Subcontracting",
    "İç Satın Alma": "Indirect",
    "Kurumsal Satın Alma": "Corporate",
    # origin
    "Yurt İçi": "Domestic",
    "Yurt Dışı": "Foreign",
    # approval
    "Limit İçi": "Within Limit",
    "Yönetim Onayı": "Management Approval",
    # status
    "Kapalı": "Closed",
    "Açık": "Open",
    "İptal": "Cancelled",
    # urgency
    "Normal": "Normal",
    "Acil": "Emergency",
    # segment
    "Stratejik": "Strategic",
    "Onaylı": "Approved",
    "Yeni": "New",
    # payment methods
    "Peşin": "Cash",
    "Vadeli 30 Gün": "Net 30",
    "Vadeli 60 Gün": "Net 60",
    "Vadeli 90 Gün": "Net 90",
    "Akreditif (LC)": "Letter of Credit",
    "Banka Havalesi": "Bank Transfer",
    "Çek": "Cheque",
    # countries
    "Türkiye": "Türkiye", "Almanya": "Germany", "Fransa": "France",
    "ABD": "USA", "İngiltere": "UK", "İtalya": "Italy", "İsviçre": "Switzerland",
}


def t(key: str, lang: str = DEFAULT_LANG) -> str:
    """Translate a UI/label key."""
    entry = _T.get(key)
    if not entry:
        return key
    return entry.get(lang, entry.get(DEFAULT_LANG, key))


def tv(value: str, lang: str = DEFAULT_LANG) -> str:
    """Translate a categorical *value* (canonical TR -> selected language)."""
    if lang == "tr" or value is None:
        return value
    return _VALUES_EN.get(value, value)
