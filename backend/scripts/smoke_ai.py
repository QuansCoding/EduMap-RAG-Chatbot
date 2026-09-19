"""Quick live check that the AI provider talks to Gemini correctly.

Run from backend/ with the venv active:  python -m scripts.smoke_ai
Makes real API calls, so it spends quota.
"""

from app.ai.provider import AIProvider, get_ai_provider
from app.config import get_settings


def main() -> None:
    settings = get_settings()
    ai = get_ai_provider()
    assert isinstance(ai, AIProvider), f"{type(ai).__name__} is not an AIProvider"

    vector = ai.embed_query("What is a mutex?")
    assert len(vector) == settings.embedding_dimensions, (
        f"expected {settings.embedding_dimensions} dimensions, got {len(vector)}"
    )
    print(f"embed_query   -> {len(vector)} dims, first value {vector[0]:.5f}")

    batch = ai.embed_documents(["A mutex guards shared state.", "A semaphore counts permits."])
    assert len(batch) == 2, f"expected 2 vectors, got {len(batch)}"
    print(f"embed_documents -> {len(batch)} vectors of {len(batch[0])} dims")

    reply = ai.generate_text("Be brief.", "Say hello in 5 words.")
    assert reply, "generate_text returned nothing"
    print(f"generate_text -> {reply!r}")

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
