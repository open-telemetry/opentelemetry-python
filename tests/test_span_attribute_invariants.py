import pytest

def validate_span_attribute(key: str, value) -> bool:
    if not isinstance(key, str) or not key.strip():
        return False
    if not isinstance(value, (str, int, float, bool, bytes)):
        return False
    return True

def test_valid_span_attributes():
    assert validate_span_attribute("http.status_code", 200) is True
    assert validate_span_attribute("db.system", "postgresql") is True
    assert validate_span_attribute("ai.request.duration_ms", 142.5) is True

def test_invalid_span_attributes():
    assert validate_span_attribute("", 200) is False
    assert validate_span_attribute("custom.key", [1, 2, 3]) is False
