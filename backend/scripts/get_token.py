import os
import sys

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict
"""
This script signs into Supabase's Auth REST API and prints a token for auth test

Creates the user if needed (requires "Confirm email" OFF), then prints access token.
"""

class ScriptSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    supabase_url: sys
    supabase_publishable_key: str

def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
    email, password = sys.argv[1], sys.argv[2]
    s = ScriptSettings()
    headers = {"apikey": s.supabase_publishable_key, "Content-Type": "application/json"}
    body = {"email": email,"password": password}

    # Try signing in; if that fails sign up
    res = httpx.post(f"{s.supabase_url}/auth/v1/token?grant_type=password", headers=headers, json=body)
    if res.status_code != 200:
        signup = httpx(f"{s.supabase_url}/auth/v1/signup", headers=headers, json=body)
        signup.raise_for_status()
        res = httpx.post(f"{s.supabase_url}/auth/v1/token?grant_type=password", headers=headers, json=body)
        res.raise_for_status()
        print(res.json()["access_token"])


if __name__ == "__main__":
    main()