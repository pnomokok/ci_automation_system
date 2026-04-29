from app.signature_validator import build_signature, is_valid_signature


def test_signature_matches_payload() -> None:
    secret = "top-secret"
    payload = b'{"hello":"world"}'
    signature = build_signature(secret, payload)
    assert is_valid_signature(secret, payload, signature) is True


def test_signature_rejects_invalid_value() -> None:
    assert is_valid_signature("secret", b"payload", "sha256=wrong") is False
