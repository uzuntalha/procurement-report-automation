"""Streamlit front-end — a thin shell over the report_generator package.

Upload (or use the bundled) procurement workbook, pick a week and a report
language, and download an executive .pptx. All heavy lifting lives in
report_generator; this file only wires UI to that pipeline.
"""

from __future__ import annotations

import io
from datetime import date

import streamlit as st

from report_generator import (
    load_workbook, build_dataset, week_options, compute_report_model,
    build_deck, ValidationError,
)
from report_generator import i18n
from report_generator.charts import fmt_try

SAMPLE_PATH = "data/sample_procurement_2026.xlsx"

st.set_page_config(page_title="Procurement Weekly Report Automation",
                   page_icon="📊", layout="centered")


@st.cache_data(show_spinner=False)
def _dataset_from_bytes(raw: bytes):
    return build_dataset(load_workbook(io.BytesIO(raw)))


@st.cache_data(show_spinner=False)
def _dataset_from_sample():
    return build_dataset(load_workbook(SAMPLE_PATH))


def main() -> None:
    # ---- interface language (sidebar) ---------------------------------- #
    with st.sidebar:
        ui = st.radio(i18n.t("ui_language", "en"), options=["en", "tr"],
                      format_func=lambda x: {"en": "English", "tr": "Türkçe"}[x])
        st.caption(i18n.t("synthetic_note", ui))

    st.title(i18n.t("app_title", ui))
    st.caption(i18n.t("app_tagline", ui))

    # ---- 1 · load workbook --------------------------------------------- #
    st.subheader(i18n.t("upload", ui))
    use_sample = st.toggle(i18n.t("use_sample", ui), value=True)
    dataset = None
    try:
        if use_sample:
            dataset = _dataset_from_sample()
        else:
            up = st.file_uploader("xlsx", type=["xlsx"],
                                  label_visibility="collapsed")
            if up is not None:
                dataset = _dataset_from_bytes(up.getvalue())
    except ValidationError as exc:
        st.error(f"⚠️ {exc}")
        st.stop()
    except Exception as exc:  # noqa: BLE001
        st.error(f"⚠️ Unexpected error while reading the workbook: {exc}")
        st.stop()

    if dataset is None:
        st.info("⬆️ " + i18n.t("upload", ui))
        st.stop()

    opts = week_options(dataset)
    if not opts:
        st.warning(i18n.t("no_data", ui))
        st.stop()

    # ---- 2 · pick week -------------------------------------------------- #
    st.subheader(i18n.t("select_week", ui))
    labels = [o["label"] for o in opts]
    default_idx = min(len(opts) - 1, len(opts) // 2)
    choice = st.selectbox("week", labels, index=default_idx,
                          label_visibility="collapsed")
    week = opts[labels.index(choice)]

    # ---- 3 · report language ------------------------------------------- #
    st.subheader(i18n.t("report_lang", ui))
    report_lang = st.radio("report language", options=["en", "tr"],
                           format_func=lambda x: {"en": "English",
                                                  "tr": "Türkçe"}[x],
                           horizontal=True, label_visibility="collapsed")

    # ---- generate ------------------------------------------------------- #
    if st.button("🛠️ " + i18n.t("generate", ui), type="primary"):
        model = compute_report_model(dataset, week["start"], week["end"])
        if not model["has_data"]:
            st.warning(i18n.t("no_data", ui))
            st.stop()

        with st.spinner(i18n.t("generate", ui) + " …"):
            pptx = build_deck(model, lang=report_lang, generated_on=date.today())

        st.success("✅ " + i18n.t("generate", ui))

        # quick on-screen preview of the headline KPIs
        k = model["kpis"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(i18n.t("kpi_spend", ui), fmt_try(k["spend"]["value"]),
                  None if k["spend"]["delta"] is None
                  else f"{k['spend']['delta']:.0%}")
        c2.metric(i18n.t("kpi_pos", ui), f"{k['pos']['value']:,}")
        c3.metric(i18n.t("kpi_approval", ui), f"{k['approval']['value']:.0%}")
        c4.metric(i18n.t("kpi_savings", ui), fmt_try(k["savings"]["value"]))

        fname = f"procurement_report_{week['start']:%Y%m%d}_{report_lang}.pptx"
        st.download_button(
            "⬇️ " + i18n.t("download", ui), data=pptx, file_name=fname,
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            type="primary")


if __name__ == "__main__":
    main()
