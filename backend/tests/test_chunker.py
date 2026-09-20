import pytest

from app.ingestion.chunker import chunk_pages
from app.ingestion.loaders import PageText

def make_page(word_count: int, page_number: int =1) -> PageText:
    return PageText(page_number=page_number, text=" ".join(f"w{i}" for i in range(word_count)))

def test_short_page_becomes_single_chunk():
    chunks = chunk_pages([make_page(100)], chunk_size=350, overlap=50)
    assert len(chunks) == 1
    assert chunks[0].page_number == 1

def test_long_page_overlaps_correctly():
    chunks = chunk_pages([make_page(800)], chunk_size=350, overlap=50)
    assert len(chunks) == 3
    first, second = chunks[0].content.split(), chunks[1].content.split()
    assert first[-50:] == second[:50]  #  the 50 word overlap
    assert chunks[-1].content.split()[-1] == "w799"  # nothing is lost at the end

def test_chunk_indexes_are_global_and_pages_preserved():
    # FIX: {} made this a set, which needs hashable elements and loses page order.
    chunks = chunk_pages([make_page(10, 1), make_page(10, 2)], chunk_size=350, overlap=50)
    assert [c.index for c in chunks] == [0, 1]
    assert [c.page_number for c in chunks] == [1, 2]

def test_invalid_overlap_raises():
    with pytest.raises(ValueError):
        chunk_pages([make_page(10)], chunk_size=50, overlap=50)


