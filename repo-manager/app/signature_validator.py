import hashlib
import hmac


def build_signature(secret: str, payload: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def is_valid_signature(secret: str, payload: bytes, provided_signature: str | None) -> bool:
    if not secret or not provided_signature:
        return False
    expected_signature = build_signature(secret, payload)
    return hmac.compare_digest(expected_signature, provided_signature)
