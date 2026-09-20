from uuid import uuid4

from app.ai.provider import AIProvider
from app.config import get_settings
from app.services import rag
from app.services.rag import RagAnswer, RetrievedChunk, build_citations, format_sources

def make_chunk(title: str = "Lecture 3", page: int = 4) -> RetrievedChunk:
    # FIX: `uuid4` passed the function itself, not a UUID — missing parentheses.
    return RetrievedChunk(uuid4(), uuid4(), title, page, "A mutex allows one thread at a time.", 0.82)

class FakeProvider(AIProvider):
    """A test double: implements the interface with canned, instant, free responses"""

    def __init__(self, answer: RagAnswer):
        self.answer = answer
        self.text_calls = 0

    def embed_documents(self, texts, title=None):
        return [[0.0] * 768 for _ in texts]

    def embed_query(self, text):
        return [0.0] * 768

    def generate_text(self, system, prompt):
        self.text_calls += 1
        return "standalone query"

    def generate_structured(self, system, prompt, schema):
        return self.answer


def test_format_sources_numbers_from_one():  # FIX: was test_format_soruces_numbers_for_one
    text = format_sources([make_chunk("A", 1), make_chunk("B", 9)])
    assert text.startswith("[1] A (page 1)")
    assert "[2] B (page 9)" in text


def test_build_citations_drops_invalid_and_duplicate_numbers():
    chunks = [make_chunk("A", 1), make_chunk("B", 2)]
    citations = build_citations([2, 2, 0, 7, 1], chunks)
    assert[c["source_number"] for c in citations] == [2, 1]
    assert citations [0]["document_title"] == "B"


def test_answer_without_valid_citations_is_labeled_general_knowledge(monkeypatch):
    monkeypatch.setattr(rag, "retrieve", lambda *args, **kwargs: [make_chunk()])
    fake = FakeProvider(RagAnswer(answer="...", key_points=[], found_in_materials=True, cited_sources=[5]))

    result, citations = rag.answer_question(fake, get_settings(), uuid4(), "What is a mutex?", history=[])

    assert citations == []
    assert result.found_in_materials is False  # the server overrode the model's claim
    assert fake.text_calls == 0  # no history → no condense call


def test_follow_up_questions_are_condensed(monkeypatch):
    monkeypatch.setattr(rag, "retrieve", lambda *args, **kwargs: [make_chunk()])
    fake = FakeProvider(RagAnswer(answer="ok [1]", key_points=["k"], found_in_materials=True, cited_sources=[1]))
    history = [{"sender": "user", "content": "What is a mutex?"}, {"sender": "assistant", "content": "A lock."}]

    result, citations = rag.answer_question(fake, get_settings(), uuid4(), "Explain it simpler", history)

    assert fake.text_calls == 1
    assert result.found_in_materials is True
    assert citations[0]["page_number"] == 4