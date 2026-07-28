import os
import types
import time
import pytest

from opentelemetry.exporter.otlp.proto.http._common import _is_retryable, _get_retry_after_seconds


class _FakeResp:
    def __init__(self, status_code: int, headers: dict[str, str] | None = None):
        self.status_code = status_code
        self.headers = headers or {}


def test_is_retryable_includes_429():
    resp = _FakeResp(429)
    assert _is_retryable(resp) is True


def test_parse_retry_after_seconds_delta():
    assert _get_retry_after_seconds({"Retry-After": "2"}) in (2.0, pytest.approx(2.0, rel=0.2))


def test_parse_retry_after_seconds_date():
    # RFC1123 date slightly in the future
    future = time.gmtime(time.time() + 1)
    header = time.strftime("%a, %d %b %Y %H:%M:%S GMT", future)
    val = _get_retry_after_seconds({"Retry-After": header})
    assert val is not None
    assert val >= 0.0


@pytest.mark.skipif("httpx" not in {m.__name__ for m in map(lambda k: types.ModuleType(k), list(__import__("sys").modules.keys()))}, reason="httpx not installed")
def test_httpx_transport_selected(monkeypatch):
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    monkeypatch.setenv("OTEL_EXPORTER_OTLP_HTTP_TRANSPORT", "httpx")
    exp = OTLPSpanExporter()
    # Import inside test to avoid ImportError when httpx missing
    try:
        from opentelemetry.exporter.otlp.proto.http._common._transport_httpx import HttpxSession
    except Exception:
        pytest.skip("httpx transport unavailable")
    assert isinstance(exp._session, HttpxSession)
