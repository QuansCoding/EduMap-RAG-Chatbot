import logging
import time
from collections.abc import Callable
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from app.ai.provider import AIProvider, AIProviderError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)
R = TypeVar("R")

RETRYABLE_STATUS_CODES = {429,500,502,503,504}

class GeminiProvider(AIProvider):
    EMBED_BATCH_SIZE = 20  # chunks per embedding request
    MAX_RETRIES = 4

    def __init__(self, api_key: str, chat_model: str, embedding_model: str, dimensions: int):
        self._client = genai.Client(api_key=api_key)
        self._chat_model = chat_model
        self._embedding_model = embedding_model
        self._dimensions= dimensions

    # Embeddings

    def embed_documents(self, texts: list[str], title: str | None = None) -> list[list[float]]:
        doc_title = title or "none"
        formatted = [f"title: {doc_title} | text: {text}" for text in texts]
        vectors: list[list[float]] = []
        for start in range(0, len(formatted), self.EMBED_BATCH_SIZE):
            batch = formatted[start : start + self.EMBED_BATCH_SIZE]
            vectors.extend(self._embed_batch(batch))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._embed_batch([f"task: serach result | query: {text}"])[0]

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        # One content per text -> one embedding per text
        contents = [types.Content(parts=[types.Part.from_text(text=t)]) for t in texts]
        result = self._with_retry(
            lambda: self._client.models.embed_content(
                model=self._embedding_model,
                contents=contents,
                config=types.EmbedContentConfig(output_dimensionality=self._dimensions),
            )
        )
        embeddings = [list(e.values) for e in result.embeddings]
        if len(embeddings) != len(texts):
            raise AIProviderError(f"Expected {len(texts)} embeddings, got {len(embeddings)}")
        return embeddings

    # Generation

    def generate_text(self, system: str, prompt: str) -> str:
        response = self._with_retry(
            lambda: self._client.models.generate_content(
                model=self._chat_model,
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=system, temperature=0.2),
            )
        )
        return (response.text or "").strip()

    def generate_structured(self, system: str, prompt: str, schema: type[T]) -> T:
        response = self._with_retry(
            lambda: self._client.models.generate_content(
                model=self._chat_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=0.2,
                    response_mime_type="application/json",  #reply with JSON only
                    response_schema=schema,  # shaped like this model
                ),
            )
        )
        if isinstance(response.parsed, schema):
            return response.parsed
        try:  # fallback: parses the raw text ourselves
            return schema.model_validate_json(response.text or "")
        except ValidationError as exc:
            raise AIProviderError("The AI returned malformed JSON") from exc

    # Helpers

    def _with_retry(self, call: Callable[[], R]):
        delay = 2.0
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                return call()
            except Exception as exc:  # the SDK raises multiple error types
                code= getattr(exc, "code", None)
                if code in RETRYABLE_STATUS_CODES and attempt < self.MAX_RETRIES:
                    logger.warning("Gemini error %s (attempt %d); retrying in %.0fs", code, attempt, delay)
                    time.sleep(delay)
                    delay *= 2
                    continue
                logger.exception("Gemini call failed")
                raise AIProviderError(str(exc)) from exc
        raise AIProviderError("Retries exhausted")  # unreachable, keeps checkers happy

    