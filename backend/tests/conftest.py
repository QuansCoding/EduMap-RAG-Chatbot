import os

# Settings() requires these; give tests harmeless fake values,
# so tests never touch real services. setdefault = don't override real env vars.

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("GEMINI_API_KEY", "test-key")
