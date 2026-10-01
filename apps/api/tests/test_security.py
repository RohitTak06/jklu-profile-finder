from uuid import uuid4

from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_verifies_without_storing_plaintext() -> None:
    password = "correct-horse-battery-staple"
    encoded = hash_password(password)

    assert encoded != password
    assert encoded.startswith("$argon2id$")
    assert verify_password(password, encoded)
    assert not verify_password("incorrect-password", encoded)


def test_access_token_round_trip_and_rejects_bad_token() -> None:
    user_id = uuid4()
    token = create_access_token(user_id)

    assert decode_access_token(token) == user_id
    assert decode_access_token("not-a-token") is None