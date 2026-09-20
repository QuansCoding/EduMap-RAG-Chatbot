from io import BytesIO

import pytest
from pypdf import PdfWriter

from app.ingestion.loaders import (
    DocumentTooLargeError,
    PdfLoader,
    UnsupportedFileTypeError,
    clean_text,
    get_loader,
)

def blank_pdf(pages: int) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()

def test_clean_text_removes_nul_and_extra_whitespace():
    assert clean_text("Hello\x00   world \n\n\n\n next") == "Hello world\n\nnext"

def test_get_loader_picks_pdf_case_insensitively():
    assert isinstance(get_loader("Lecture1.PDF", max_pages=10), PdfLoader)


def test_get_loader_rejects_unknown_extension():
    with pytest.raises(UnsupportedFileTypeError):
        get_loader("notes.docx", max_pages=10)


def test_blank_pdf_yields_no_pages():
    assert PdfLoader(max_pages=10).load(blank_pdf(2)) == []


def test_pdf_page_limit():
    with pytest.raises(DocumentTooLargeError):
        PdfLoader(max_pages=2).load(blank_pdf(3))