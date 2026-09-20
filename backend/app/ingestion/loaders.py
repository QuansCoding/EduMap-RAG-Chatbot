import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader


@dataclass
class PageText:
    page_number: int  # 1-based, since humans count pages
    text: str

class UnsupportedFileTypeError(ValueError):
    pass

class DocumentTooLargeError(ValueError):
    pass

def clean_text(text: str) -> str:
    """Normalize extracted text so that chunks are compact and database-safe"""
    text = text.replace("\x00", "")  # Postgres TEXT can't store NUL bytes (common in PDFs)
    text = text.replace("\r\n", "\n").replace("\r","\n")  # normalize Window/Mac line endings
    text = re.sub(r"[ \t\f\v]+", " ", text)  # collapses runs of space/tabs
    text = re.sub(r" *\n *", "\n", text)  # trims spaces around line breaks
    text = re.sub(r"\n{3,}", "\n\n", text)  # at most one blank line
    return text.strip()


class DocumentLoader(ABC):
    """Turns raw file bytes into a list of pages of text."""

    extensions: tuple[str, ...] = ()

    @abstractmethod
    def load(self, data: bytes) -> list[PageText]: ...


class PdfLoader(DocumentLoader):
    extensions = (".pdf",)

    def __init__(self, max_pages: int):
        self.max_pages = max_pages

    def load(self, data:bytes) -> list[PageText]:
        reader = PdfReader(BytesIO(data))
        if len(reader.pages) > self.max_pages:
            raise DocumentTooLargeError(
                f"PDF has {len(reader.pages)} pages; the limit is {self.max_pages}. "
                "Try uploading individual chapters."
            )
        pages: list[PageText] = []
        for number, page in enumerate(reader.pages, start=1):
            text= clean_text(page.extract_text() or "")
            if text:  #skips blank pages (and image-only pages)
                pages.append(PageText(page_number=number, text=text))
        return pages


def get_loader(filename: str, max_pages: int) -> DocumentLoader:
    """Registry/factory: pick a loader by a file extension."""
    extension = os.path.splitext(filename.lower())[1]
    loaders: list[DocumentLoader] = [
        PdfLoader(max_pages),
        # Add other future formats (like DocxLoader or PptxLoader)
    ]
    for loader in loaders:
        if extension in loader.extensions:
            return loader
    supported = ", ".join(ext for loader in loaders for ext in loader.extensions)
    raise UnsupportedFileTypeError(f"Unsupported file type '{extension or 'none'}'. Supported: {supported}")