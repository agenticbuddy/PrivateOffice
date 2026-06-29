"""Blank OOXML document generation.

New documents are created from the library's neutral OOXML defaults. We deliberately do
NOT stamp a content/default language onto the document: the Collabora/LibreOffice core
derives metric-field formatting (e.g. the point measurement unit) and the status-bar
language tag from the document's CONTENT language, not from the editor UI language. Pinning
that content language to the creator's UI locale therefore made the unit render in that
locale (e.g. Cyrillic "пт") for every viewer regardless of their UI language. The editor's
UI language is supplied separately at open time via the ``lang`` URL parameter, and the
creator's locale is preserved independently in the ``creator_locale`` node metadata.
"""
from io import BytesIO

from docx import Document
from openpyxl import Workbook
from pptx import Presentation


def _docx() -> bytes:
    doc = Document()
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _xlsx() -> bytes:
    wb = Workbook()
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _pptx() -> bytes:
    prs = Presentation()
    buf = BytesIO()
    prs.save(buf)
    return buf.getvalue()


_BUILDERS = {"docx": _docx, "xlsx": _xlsx, "pptx": _pptx}


def blank_document(fmt: str) -> bytes:
    """Return bytes of a blank document of the given format (neutral language default)."""
    if fmt not in _BUILDERS:
        raise ValueError(f"Unsupported creatable format: {fmt}")
    return _BUILDERS[fmt]()
