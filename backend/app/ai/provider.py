from abc import ABC, abstractmethod
from functools import lru_cache
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class AIProvider(ABC):
    """Everything the app needs from an AI vendor.
    Subclasses must implement every @abstractmethod and
    Python refuses to instantiate a subclass that doesn't"""

    @abstractmethod
    def embed_documents(self, text: list[str], title: str | None = None) -> list[list[float]]:
        """Embed chunk of a document for storgae. Returns one vector per text in the same order."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a search query"""

    @abstractmethod
    def generate_text(self, system: str, promt: str) -> str:
        """Free-form text generation."""

    @abstractmethod
    def generate_structured(self, system: str, prompt: str, schema: type[T]) -> T:
        """Generate JSON that matches a Pydantic model and returns it parsed."""

class AIProviderError(RuntimeError):
    """Raised when the AI vendor fails after retries.
    (could be from rate limits, outage or a bad output)."""


@lru_cache
def get_ai_provider() -> AIProvider:
    """The one place that decides what cencrete provider the app actually uses."""
    from app.ai.gemini_provider import GeminiProvider
    from app.config import get_settings

    s = get_settings()
    return GeminiProvider(
        api_key=s.gemini_api_key,
        chat_model=s.chat_model,
        embedding_model=s.embedding_model,
        dimensions=s.embedding_dimensions,
    )