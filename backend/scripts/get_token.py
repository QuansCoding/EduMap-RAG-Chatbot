"""
This script signs into Supabase's Auth REST API and prints a token for auth test

Usage (from backend/, venv active):
    python scripts/get_token.py you@example.com yourpassword

Creates the user if needed (requires "Confirm email" OFF), then prints access token.
"""
# FIX: this docstring sat below the imports, so it wasn't the module docstring at all
# and `print(__doc__)` below printed "None". A docstring must be the first statement.

import sys

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScriptSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    supabase_url: str  # FIX: was annotated `sys` (the module) instead of `str`.
    supabase_publishable_key: str

def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)  # FIX: without this it fell through to an IndexError on argv[1].
    email, password = sys.argv[1], sys.argv[2]
    s = ScriptSettings()
    headers = {"apikey": s.supabase_publishable_key, "Content-Type": "application/json"}
    body = {"email": email,"password": password}

    # Try signing in; if that fails sign up
    res = httpx.post(f"{s.supabase_url}/auth/v1/token?grant_type=password", headers=headers, json=body)
    if res.status_code != 200:
        # FIX: was `httpx(...)` — a module isn't callable; it needs httpx.post.
        signup = httpx.post(f"{s.supabase_url}/auth/v1/signup", headers=headers, json=body)
        signup.raise_for_status()
        res = httpx.post(f"{s.supabase_url}/auth/v1/token?grant_type=password", headers=headers, json=body)
    # FIX: these two were indented inside the `if`, so a successful sign-in printed nothing.
    res.raise_for_status()
    print(res.json()["access_token"])


if __name__ == "__main__":
    main()