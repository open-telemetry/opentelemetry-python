# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import ssl
import warnings
from unittest.mock import Mock, patch
from urllib.error import URLError
from urllib.request import HTTPSHandler, build_opener

import pytest

from opentelemetry.exporter.otlp.proto.http._common import (
    _is_retryable,
    _load_provider_from_envvar,
    _resolve_client,
)


# ── _is_retryable ─────────────────────────────────────────────────────────────

def test_is_retryable_408():
    assert _is_retryable(408) is True


def test_is_retryable_500():
    assert _is_retryable(500) is True


def test_is_retryable_503():
    assert _is_retryable(503) is True


def test_is_retryable_599():
    assert _is_retryable(599) is True


def test_is_retryable_200():
    assert _is_retryable(200) is False


def test_is_retryable_404():
    assert _is_retryable(404) is False


def test_is_retryable_400():
    assert _is_retryable(400) is False


# ── _load_provider_from_envvar ────────────────────────────────────────────────

_CRED_ENVVAR = "OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER"
_GENERIC_ENVVAR = "OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER"


def test_load_provider_returns_none_when_no_env_var():
    with patch.dict("os.environ", {}, clear=True):
        assert _load_provider_from_envvar(_CRED_ENVVAR) is None


def test_load_provider_raises_on_unknown_provider():
    with patch.dict("os.environ", {_GENERIC_ENVVAR: "nonexistent_provider"}):
        with pytest.raises(RuntimeError, match="not found in entry point"):
            _load_provider_from_envvar(_CRED_ENVVAR)


def test_load_provider_returns_value_from_provider():
    sentinel = Mock()
    mock_ep = Mock()
    mock_ep.load.return_value = lambda: sentinel
    with patch.dict("os.environ", {_GENERIC_ENVVAR: "my_provider"}):
        with patch(
            "opentelemetry.exporter.otlp.proto.http._common.entry_points",
            return_value=iter([mock_ep]),
        ):
            assert _load_provider_from_envvar(_CRED_ENVVAR) is sentinel


# ── _resolve_client ───────────────────────────────────────────────────────────

_CTX = ssl.create_default_context()


def test_resolve_client_default_is_opener_without_warning():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with patch.dict("os.environ", {}, clear=True):
            client = _resolve_client(None, _CRED_ENVVAR, _CTX)
    assert callable(client)


def test_resolve_client_accepts_opener_director_without_warning():
    opener = build_opener(HTTPSHandler(context=_CTX))
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        client = _resolve_client(opener, _CRED_ENVVAR, _CTX)
    assert callable(client)


def test_resolve_client_session_is_deprecated_but_routed():
    class _Resp:
        status_code = 200
        reason = "OK"

    session = Mock()
    session.post.return_value = _Resp()
    with pytest.warns(DeprecationWarning):
        client = _resolve_client(session, _CRED_ENVVAR, _CTX)
    status, reason = client("http://endpoint", b"data", {"k": "v"}, 3.0)
    assert (status, reason) == (200, "OK")
    session.post.assert_called_once_with(
        "http://endpoint", data=b"data", headers={"k": "v"}, timeout=3.0
    )


def test_resolve_client_session_transport_error_becomes_urlerror():
    session = Mock()
    session.post.side_effect = OSError("boom")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        client = _resolve_client(session, _CRED_ENVVAR, _CTX)
    with pytest.raises(URLError):
        client("http://endpoint", b"data", {}, 1.0)


def test_resolve_client_rejects_invalid_injectable():
    with pytest.raises(RuntimeError, match="OpenerDirector"):
        _resolve_client(object(), _CRED_ENVVAR, _CTX)
