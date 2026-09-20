from dataclasses import dataclass

from app.ingestion.loaders import PageText

@dataclass
class Chunk:
    index: int  # Position within the whole document
    page_number: int
    content: str

def chunk_pages(pages: list[PageText], chunk_size: int = 350, overlap: int = 50) -> list[Chunk]:
    """Splits each page into overlapping word windows.
    
    Ex. with chunk_size=350, overlap=50 on an 800-word page:
        window 1: words 0-349
        window 2: words 300-649 (starts at 300 since there is a 50 overlap)
        window 3: words 600-799
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if not 0 <= overlap < chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    step = chunk_size - overlap
    chunks: list[Chunk] = []
    for page in pages:
        words = page.text.split()
        for start in range(0, len(words), step):
            window = words[start : start + chunk_size]
            chunks.append(Chunk(index=len(chunks),page_number=page.page_number, content=" ".join(window)))
            if start + chunk_size >= len(words):  # this window has reached the end of the apge
                break
    return chunks