# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import Mock, patch

import pytest

from opentelemetry.exporter.otlp.proto.http._common import (
    _is_retryable,
    _load_session_from_envvar,
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


# ── _load_session_from_envvar ─────────────────────────────────────────────────

_CRED_ENVVAR = "OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER"
_GENERIC_ENVVAR = "OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER"


def test_load_session_returns_none_when_no_env_var():
    with patch.dict("os.environ", {}, clear=True):
        result = _load_session_from_envvar(_CRED_ENVVAR)
    assert result is None


def test_load_session_raises_on_unknown_provider():
    with patch.dict("os.environ", {_GENERIC_ENVVAR: "nonexistent_provider"}):
        with pytest.raises(RuntimeError, match="not found in entry point"):
            _load_session_from_envvar(_CRED_ENVVAR)


def test_load_session_returns_value_from_provider():
    mock_session = Mock()
    mock_ep = Mock()
    mock_ep.load.return_value = lambda: mock_session

    with patch.dict("os.environ", {_GENERIC_ENVVAR: "my_provider"}):
        with patch(
            "opentelemetry.exporter.otlp.proto.http._common.entry_points",
            return_value=iter([mock_ep]),
        ):
            result = _load_session_from_envvar(_CRED_ENVVAR)
    assert result is mock_session
