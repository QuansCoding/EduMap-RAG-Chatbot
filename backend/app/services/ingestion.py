import logging
from uuid import UUID

from app.ai.provider import get_ai_provider
from app.config import get_settings
from app.db import get_conn, to_pgvector
from app.ingestion.chunker import chunk_pages
from app.ingestion.loaders import get_loader

logger = logging.getLogger(__name__)

def process_document(document_id: UUID, workspace_id: UUID, title: str, filename: str, data: bytes) -> None:
    """Extract → chunk → embed → store. Runs in the background after the upload returns.
    Any failure marks the document as 'failed' with a readable message."""
    settings = get_settings()
    try:
        loader = get_loader(filename, settings.max_pdf_pages)
        pages = loader.load(data)
        if not pages:
            raise ValueError("No extractable text found. Is this a scanned (image-only) PDF?")

        chunks = chunk_pages(pages, settings.chunk_size_words, settings.chunk_overlap_words)
        logger.info("Document %s: %d pages with text, %d chunks", document_id, len(pages), len(chunks))

        # The slow part: network calls to the embedding API.
        # Done BEFORE opening a DB connection so we don't hold a connection idle for 30s.
        embeddings = get_ai_provider().embed_documents([c.content for c in chunks], title=title)

        with get_conn() as conn:  # one transaction: all chunks + status update, or nothing
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO document_chunks
                        (document_id, workspace_id, chunk_index, page_number, content, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s::vector)
                    """,
                    [
                        (document_id, workspace_id, c.index, c.page_number, c.content, to_pgvector(vec))
                        for c, vec in zip(chunks, embeddings, strict=True)
                    ],
                )
            conn.execute(
                "UPDATE documents SET status = 'ready', page_count = %s, chunk_count = %s WHERE id = %s",
                (pages[-1].page_number, len(chunks), document_id),
            )
        logger.info("Document %s ready", document_id)

    except Exception as exc:  # we WANT to catch everything here and record it
        logger.exception("Document %s failed", document_id)
        with get_conn() as conn:
            conn.execute(
                "UPDATE documents SET status = 'failed', error_message = %s WHERE id = %s",
                (str(exc)[:500], document_id),
            )