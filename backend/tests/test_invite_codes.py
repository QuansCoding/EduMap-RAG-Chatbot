from app.services.invite_codes import INVITE_ALPHABET, generate_invite_code, normalize_invite_code

def test_invite_code_shape():
    code = generate_invite_code()
    assert len(code) == 8
    assert all(ch in INVITE_ALPHABET for ch in code)

def test_invite_codes_are_random():
    # FIX: the closing brace was misplaced, making this a generator of 1000 single-item
    # sets instead of one set comprehension collecting 1000 codes.
    assert len({generate_invite_code() for _ in range(1000)}) == 1000

def test_normalize():
    assert normalize_invite_code("  ab3d-ef9h ") == "AB3DEF9H"