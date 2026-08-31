"""Procurement weekly report generator — pure logic package.

Pipeline: parsing (load + validate) -> metrics (enrich + aggregate)
-> charts (matplotlib) -> deck (python-pptx assembly).
The Streamlit app in ``app.py`` is a thin shell over this package.
"""

from .parsing import load_workbook, ValidationError
from .metrics import build_dataset, week_options, compute_report_model
from .deck import build_deck

__all__ = [
    "load_workbook",
    "ValidationError",
    "build_dataset",
    "week_options",
    "compute_report_model",
    "build_deck",
]
