"""Assemble the 13-slide PowerPoint deck with python-pptx.

Charts (from ``charts.py``) are embedded as images; titles, KPI cards and the
highlights table are native PowerPoint shapes. The deck is bilingual — all
display strings come from ``i18n`` in the selected report language.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass
from datetime import date

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

from . import i18n
from .charts import Charts, fmt_try, INK, ACCENT, POS, NEG, WITHIN, MUTED, LIGHT

_INK = RGBColor(0x1B, 0x2A, 0x4A)
_ACCENT = RGBColor(0x2F, 0x6D, 0xB4)
_POS = RGBColor(0x2E, 0x8B, 0x6F)
_NEG = RGBColor(0xC0, 0x50, 0x4D)
_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
_LIGHT = RGBColor(0xED, 0xF2, 0xF8)
_GREY = RGBColor(0x6B, 0x74, 0x80)


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float


class DeckBuilder:
    def __init__(self, lang: str = "en"):
        self.lang = lang
        self.prs = Presentation()
        self.prs.slide_width = Inches(13.333)
        self.prs.slide_height = Inches(7.5)
        self.blank = self.prs.slide_layouts[6]
        self.charts = Charts(lang=lang)

    # ------------------------------------------------------------------ #
    # low-level helpers
    # ------------------------------------------------------------------ #
    def _slide(self):
        return self.prs.slides.add_slide(self.blank)

    def _rect(self, slide, box, fill, line=None):
        shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                     Inches(box.x), Inches(box.y),
                                     Inches(box.w), Inches(box.h))
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
        if line is None:
            shp.line.fill.background()
        else:
            shp.line.color.rgb = line
        shp.shadow.inherit = False
        return shp

    def _text(self, slide, box, text, size, color=_INK, bold=False,
              align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, font="Calibri"):
        tb = slide.shapes.add_textbox(Inches(box.x), Inches(box.y),
                                      Inches(box.w), Inches(box.h))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = anchor
        p = tf.paragraphs[0]
        p.alignment = align
        r = p.add_run()
        r.text = text
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = font
        return tb

    def _title_band(self, slide, title):
        self._rect(slide, Box(0, 0, 13.333, 0.95), _INK)
        self._rect(slide, Box(0, 0.95, 13.333, 0.06), _ACCENT)
        self._text(slide, Box(0.55, 0, 12.2, 0.95), title, 24, _WHITE,
                   bold=True, anchor=MSO_ANCHOR.MIDDLE)

    def _footer(self, slide, page):
        self._text(slide, Box(0.55, 7.05, 9.0, 0.4),
                   i18n.t("synthetic_note", self.lang), 9, _GREY)
        self._text(slide, Box(11.8, 7.05, 1.0, 0.4), str(page), 9, _GREY,
                   align=PP_ALIGN.RIGHT)

    def _place_image(self, slide, path, box: Box):
        pic = slide.shapes.add_picture(path, Inches(box.x), Inches(box.y))
        aspect = pic.width / pic.height
        bw, bh = Inches(box.w), Inches(box.h)
        if bw / bh > aspect:
            h = bh
            w = int(bh * aspect)
        else:
            w = bw
            h = int(bw / aspect)
        pic.width, pic.height = w, h
        pic.left = Inches(box.x) + (bw - w) // 2
        pic.top = Inches(box.y) + (bh - h) // 2

    def _chart_slide(self, title, images, page, caption=None):
        slide = self._slide()
        self._title_band(slide, title)
        img_h = 5.5 if not caption else 5.0
        if len(images) == 1:
            self._place_image(slide, images[0], Box(0.7, 1.25, 11.93, img_h))
        else:
            self._place_image(slide, images[0], Box(0.4, 1.3, 6.2, img_h - 0.1))
            self._place_image(slide, images[1], Box(6.75, 1.3, 6.2, img_h - 0.1))
        if caption:
            self._text(slide, Box(0.7, 1.3 + img_h + 0.1, 11.9, 0.5), caption,
                       13, _ACCENT, bold=True, align=PP_ALIGN.CENTER)
        self._footer(slide, page)
        return slide

    # ------------------------------------------------------------------ #
    # slides
    # ------------------------------------------------------------------ #
    def _cover(self, model, generated_on):
        slide = self._slide()
        self._rect(slide, Box(0, 0, 13.333, 7.5), _INK)
        self._rect(slide, Box(0, 4.35, 13.333, 0.05), _ACCENT)
        self._text(slide, Box(0.9, 2.2, 11.5, 1.2),
                   i18n.t("deck_title", self.lang), 40, _WHITE, bold=True)
        ws, we = model["week_start"], model["week_end"]
        sub = f"{i18n.t('week_of', self.lang)}  {ws:%d %b %Y} – {we:%d %b %Y}"
        self._text(slide, Box(0.9, 3.4, 11.5, 0.8), sub, 20,
                   RGBColor(0xC7, 0xD6, 0xE8))
        self._text(slide, Box(0.9, 4.6, 11.5, 0.5),
                   i18n.t("synthetic_note", self.lang), 12,
                   RGBColor(0x9A, 0xA5, 0xB1))
        self._text(slide, Box(0.9, 6.7, 11.5, 0.5),
                   f"{i18n.t('generated_on', self.lang)}: {generated_on:%d %b %Y}",
                   11, RGBColor(0x9A, 0xA5, 0xB1))

    def _exec_summary(self, model, page):
        slide = self._slide()
        self._title_band(slide, i18n.t("s_exec", self.lang))
        k = model["kpis"]
        cards = [
            ("kpi_spend", fmt_try(k["spend"]["value"]), k["spend"]["delta"]),
            ("kpi_pos", f"{k['pos']['value']:,}", k["pos"]["delta"]),
            ("kpi_savings", fmt_try(k["savings"]["value"]), k["savings"]["delta"]),
            ("kpi_approval", f"{k['approval']['value']:.0%}", None),
            ("kpi_foreign", f"{k['foreign']['value']:.0%}", None),
            ("kpi_emergency", f"{k['emergency']['value']:.0%}", None),
            ("kpi_otd", ("—" if k["otd"]["value"] is None
                         else f"{k['otd']['value']:.0%}"), None),
            ("kpi_lines", f"{k['lines']['value']:,}", k["lines"]["delta"]),
        ]
        x0, y0, cw, ch, gx, gy = 0.55, 1.35, 3.0, 2.35, 0.19, 0.3
        for i, (key, val, delta) in enumerate(cards):
            r, c = divmod(i, 4)
            bx = x0 + c * (cw + gx)
            by = y0 + r * (ch + gy)
            self._rect(slide, Box(bx, by, cw, ch), _LIGHT)
            self._rect(slide, Box(bx, by, 0.09, ch), _ACCENT)
            self._text(slide, Box(bx + 0.25, by + 0.25, cw - 0.4, 0.5),
                       i18n.t(key, self.lang), 12.5, _GREY, bold=True)
            self._text(slide, Box(bx + 0.22, by + 0.7, cw - 0.4, 1.0),
                       val, 30, _INK, bold=True)
            if delta is not None:
                arrow = "▲" if delta >= 0 else "▼"
                col = _POS if delta >= 0 else _NEG
                self._text(slide, Box(bx + 0.25, by + 1.75, cw - 0.4, 0.45),
                           f"{arrow} {abs(delta):.0%}  {i18n.t('vs_prev', self.lang)}",
                           11, col)
        self._footer(slide, page)

    def _highlights(self, model, page):
        slide = self._slide()
        self._title_band(slide, i18n.t("s_highlights", self.lang))
        df = model["highlights"]
        ex = model["exceptions"]
        headers = [i18n.t(h, self.lang) for h in
                   ("col_po", "col_supplier", "col_buyer", "col_amount",
                    "col_type", "col_flag")]
        rows = len(df) + 1
        table = slide.shapes.add_table(
            rows, 6, Inches(0.55), Inches(1.35),
            Inches(12.2), Inches(0.5 * rows)).table
        widths = [1.9, 3.3, 2.4, 1.9, 1.7, 1.0]
        for c, w in enumerate(widths):
            table.columns[c].width = Inches(w)
        for c, h in enumerate(headers):
            cell = table.cell(0, c)
            cell.text = h
            cell.fill.solid()
            cell.fill.fore_color.rgb = _INK
            para = cell.text_frame.paragraphs[0]
            para.font.size = Pt(12)
            para.font.bold = True
            para.font.color.rgb = _WHITE
        for i, (_, row) in enumerate(df.iterrows(), start=1):
            flags = []
            if row["urgency"] == "Acil":
                flags.append(i18n.t("flag_emergency", self.lang))
            if row["segment"] == "Yeni":
                flags.append(i18n.t("flag_new_supplier", self.lang))
            if row["approval"] == "Yönetim Onayı" and not flags:
                flags.append(i18n.t("flag_mgmt", self.lang))
            values = [row["PO No"], str(row["supplier"]), str(row["buyer"]),
                      fmt_try(row["amount"]), i18n.tv(row["ptype"], self.lang),
                      ", ".join(flags) or "—"]
            for c, v in enumerate(values):
                cell = table.cell(i, c)
                cell.text = v
                para = cell.text_frame.paragraphs[0]
                para.font.size = Pt(11)
                para.font.color.rgb = _INK
                if c == 0:
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = _LIGHT
        note = (f"{i18n.t('flag_new_supplier', self.lang)}: {ex['new_suppliers']}   ·   "
                f"{i18n.t('flag_emergency', self.lang)}: {ex['emergency']}   ·   "
                f"{i18n.t('flag_mgmt', self.lang)}: {ex['mgmt_approvals']}")
        self._text(slide, Box(0.55, 1.4 + 0.5 * rows + 0.15, 12.2, 0.5),
                   note, 13, _ACCENT, bold=True)
        self._footer(slide, page)

    def _scorecard_slide(self, model, page):
        slide = self._slide()
        self._title_band(slide, i18n.t("s_scorecard", self.lang))
        df = model["supplier_scorecard"]
        headers = [i18n.t(h, self.lang) for h in
                   ("col_supplier", "col_spend", "col_otd", "col_defect",
                    "col_segment")]
        rows = len(df) + 1
        table = slide.shapes.add_table(
            rows, 5, Inches(0.7), Inches(1.35),
            Inches(11.9), Inches(0.5 * rows)).table
        for c, w in enumerate([4.4, 2.4, 1.7, 1.6, 1.8]):
            table.columns[c].width = Inches(w)
        for c, h in enumerate(headers):
            cell = table.cell(0, c)
            cell.text = h
            cell.fill.solid()
            cell.fill.fore_color.rgb = _INK
            p = cell.text_frame.paragraphs[0]
            p.font.size, p.font.bold, p.font.color.rgb = Pt(12), True, _WHITE
        for i, (_, row) in enumerate(df.iterrows(), start=1):
            otd_v = row["otd"]
            otd = ("—" if otd_v is None or (isinstance(otd_v, float)
                                            and math.isnan(otd_v))
                   else f"{otd_v:.0%}")
            vals = [str(row["supplier"]), fmt_try(row["spend"]), otd,
                    f"{row['defect']:.0%}", i18n.tv(row["segment"], self.lang)]
            for c, v in enumerate(vals):
                cell = table.cell(i, c)
                cell.text = v
                p = cell.text_frame.paragraphs[0]
                p.font.size, p.font.color.rgb = Pt(11), _INK
                if c == 0:
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = _LIGHT
        self._footer(slide, page)

    def _dpo_slide(self, model, page):
        slide = self._slide()
        self._title_band(slide, i18n.t("s_dpo", self.lang))
        img = self.charts.hbar(model["payment_spend"], "payment", WITHIN,
                               value_labels=False)
        self._place_image(slide, img, Box(0.4, 1.5, 7.7, 5.0))
        bx, by, cw, ch = 8.5, 2.4, 4.2, 2.3
        self._rect(slide, Box(bx, by, cw, ch), _LIGHT)
        self._rect(slide, Box(bx, by, 0.09, ch), _ACCENT)
        self._text(slide, Box(bx + 0.25, by + 0.25, cw - 0.4, 0.9),
                   i18n.t("kpi_dpo", self.lang), 13, _GREY, bold=True)
        self._text(slide, Box(bx + 0.22, by + 1.0, cw - 0.4, 1.1),
                   f"{model['dpo']:.0f} {i18n.t('days', self.lang)}",
                   34, _INK, bold=True)
        self._footer(slide, page)

    # ------------------------------------------------------------------ #
    # orchestration
    # ------------------------------------------------------------------ #
    def build(self, model, generated_on: date | None = None) -> bytes:
        generated_on = generated_on or date.today()
        c = self.charts

        self._cover(model, generated_on)
        self._exec_summary(model, 2)
        self._chart_slide(i18n.t("s_wow", self.lang),
                          [c.wow_scorecard(model["wow"], "wow")], 3)
        self._chart_slide(i18n.t("s_ptype", self.lang),
                          [c.grouped_hbar(model["ptype_compare"], "ptype")], 4)
        self._chart_slide(i18n.t("s_buyer", self.lang),
                          [c.stacked_buyer(model["buyer_stack"], "buyer")], 5)
        self._chart_slide(i18n.t("s_approval", self.lang),
                          [c.donut(model["approval_spend"], "approval",
                                   center=f"{model['kpis']['approval']['value']:.0%}\nmgmt")], 6)
        self._chart_slide(i18n.t("s_contract", self.lang),
                          [c.contract_panel(model, "contract")], 7)
        tail = model["tail"]
        self._chart_slide(
            i18n.t("s_supplier", self.lang),
            [c.pareto(model["supplier_pareto"], "supplier")], 8,
            caption=i18n.t("tail_body", self.lang).format(
                n80=tail["n80"], tail=tail["tail_count"],
                share=tail["tail_share"]))
        self._scorecard_slide(model, 9)
        self._chart_slide(i18n.t("s_origin", self.lang),
                          [c.donut(model["origin_spend"], "origin"),
                           c.hbar(model["country_spend"], "country", ACCENT,
                                  value_labels=False)], 10)
        self._chart_slide(i18n.t("s_category", self.lang),
                          [c.hbar(model["category_spend"], "category", ACCENT,
                                  value_labels=False)], 11)
        self._dpo_slide(model, 12)
        self._chart_slide(i18n.t("s_trend", self.lang),
                          [c.trend(model["trend"], model["trend_marker"], "trend")], 13)
        self._chart_slide(i18n.t("s_savings", self.lang),
                          [c.waterfall(model["savings_waterfall"], "waterfall"),
                           c.hbar(model["savings_by_ptype"], "savings_type", POS,
                                  value_labels=False)], 14)
        self._chart_slide(i18n.t("s_budget", self.lang),
                          [c.budget_actual(model["budget_actual"], "budget")], 15)
        self._chart_slide(i18n.t("s_risk", self.lang),
                          [c.risk_panel(model, "risk")], 16)
        self._highlights(model, 17)

        buf = io.BytesIO()
        self.prs.save(buf)
        return buf.getvalue()


def build_deck(model, lang: str = "en", generated_on: date | None = None) -> bytes:
    """Convenience wrapper: build the deck and return .pptx bytes."""
    return DeckBuilder(lang=lang).build(model, generated_on=generated_on)
