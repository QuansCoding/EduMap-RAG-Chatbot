from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.db import get_conn

# auto_error=False: we raise our own clean 401 instead of FastAPI's 403

bearer_scheme = HTTPBearer(auto_error=False)

_jwks_client: jwt.PyJWKClient | None = None

@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None


def _get_jwks_client() -> jwt.PyJWKClient:
    """PyJKWClient downloads Supabase's public signing keys and caches them,
    so we don't hit the netowrk each request
    """
    global _jwks_client
    if _jwks_client is None:
        # FIX: was "/auth/v1.well-known/..." — the missing slash 404s, so no token ever verifies.
        jwks_url = f"{get_settings().supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        _jwks_client = jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
    return _jwks_client


def decode_supabase_token(token: str) -> dict:
   """Verify signature, expiry, audience and issuer. Raises jwt.PYTError if
   anything is wrong."""
   settings = get_settings()
   # Token header says which key (kid) signed it; fetches that public key
   signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
   return jwt.decode(
      token,
      signing_key.key,
      algorithms=["ES256", "RS256"],  # asymmetric only; will nevery accept "none" or HS256
      audience="authenticated",       # Supabase sets aud="authenticated" for signed-in users
      # FIX: strip('/') -> rstrip('/'); we only want to drop a trailing slash.
      issuer=f"{settings.supabase_url.rstrip('/')}/auth/v1",
   )

def get_current_user(
      credentials: HTTPAuthorizationCredentials | None = Depends (bearer_scheme),
) -> CurrentUser:
   """FastAPI dependency: turns auth header into a verified CurrentUser."""
   if credentials is None:
      raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing Authorization header")

   try:
      claims = decode_supabase_token(credentials.credentials)
   # FIX: was a bare `except:`, which also swallowed real bugs (and Ctrl-C) and
   # reported every one of them as a 401. Catch only token errors.
   except jwt.PyJWTError:
      # Don't leak the *why* (expired? forged?) as it helps attackers
      raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

   user = CurrentUser(id=claims["sub"], email=claims.get("email"))

   # Make sure the user exits OUR user table (first rquest after sign-up)

   with get_conn() as conn:
      conn.execute(
         "INSERT INTO users (id, email) VALUES (%s, %s) ON CONFLICT(id) DO NOTHING",
         (user.id, user.email),
      )
      return user