from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """All Configs, loaded from environment variables (backend/.env)
    
    Field names map to env vars case-insensitively (database_url <- DATABASE_URL)
    Fields w/o a default are REQUIRED; the app will refuse to start w/o them.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Required
    database_url: str
    supabase_url: str
    gemini_api_key: str

    # AI models
    chat_model: str = "gemini-3.5-flash"
    embedding_model: str = "gemini-embedding-2"
    embedding_dimensions: int = 768  # must match vector(768) in schema.sql

    # Web
    allowed_origins: str = "http://localhost:3000"

    # Ingestions (inputs)
    max_upload_mb: int = 10
    max_pdf_pages: int = 150
    chunk_size_words: int = 350      # ~500 tokens
    chunk_overlap_words: int = 50

    # Retrival
    retrieval_top_k: int = 6
    min_similarity: float = 0.35     # chunks less similar than this are ignored

    # Usage limits (per rolling 24 hours)
    daily_chat_limit: int = 40
    daily_upload_limit: int = 10
    daily_roadmap_limit: int = 5
    global_daily_ai_limit: int = 400
    demo_email: str = "demo@edumap.app"
    demo_daily_limit: int = 10

    @property
    def origins_list(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Create settings once and reuses it (memoization)"""
    return Settings()