import secrets

# No 0/O or 1/I/L: Codes get read aloud, and typed by hand.
INVITE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

def generate_invite_code(length: int = 8) -> str:
    """Cyptographically secure random code. 31^8 ~ 850 billion possibilities"""

def normalize_invite_code(code: str) -> str:
    return code.strip().upper().replace(" ", "").replace("-","")