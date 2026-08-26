# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from logging import WARNING
from unittest.mock import patch

import pytest

from opentelemetry.exporter.otlp.proto.common._internal import (
    _timeout_from_env,
)


@pytest.mark.parametrize(
    "environ,keys,default,expected,warns_for",
    [
        pytest.param(
            {"TEST_TIMEOUT": "15"},
            ("TEST_TIMEOUT",),
            10,
            15,
            None,
            id="valid value",
        ),
        pytest.param(
            {},
            ("TEST_TIMEOUT",),
            10,
            10,
            None,
            id="unset falls back to default",
        ),
        pytest.param(
            {},
            ("TEST_TIMEOUT",),
            None,
            None,
            None,
            id="unset with no default returns None",
        ),
        pytest.param(
            {"TEST_TIMEOUT": " "},
            ("TEST_TIMEOUT",),
            10,
            10,
            None,
            id="empty/whitespace falls back to default",
        ),
        pytest.param(
            {"TEST_TIMEOUT": "abc"},
            ("TEST_TIMEOUT",),
            10,
            10,
            "TEST_TIMEOUT",
            id="invalid value warns and falls back to default",
        ),
        pytest.param(
            {"TEST_SIGNAL_TIMEOUT": "5", "TEST_TIMEOUT": "15"},
            ("TEST_SIGNAL_TIMEOUT", "TEST_TIMEOUT"),
            10,
            5,
            None,
            id="first key takes priority",
        ),
        pytest.param(
            {"TEST_SIGNAL_TIMEOUT": "abc", "TEST_TIMEOUT": "15"},
            ("TEST_SIGNAL_TIMEOUT", "TEST_TIMEOUT"),
            10,
            15,
            "TEST_SIGNAL_TIMEOUT",
            id="invalid first key warns and falls back to next key",
        ),
    ],
)
def test_timeout_from_env(caplog, environ, keys, default, expected, warns_for):
    """``warns_for`` names the environment variable the warning must mention,
    or is ``None`` when no warning is expected."""
    with (
        patch.dict("os.environ", environ, clear=True),
        caplog.at_level(WARNING),
    ):
        result = _timeout_from_env(*keys, default=default)

    assert result == expected
    if warns_for is None:
        assert not caplog.records
    else:
        assert len(caplog.records) == 1
        assert "Invalid value" in caplog.records[0].message
        assert warns_for in caplog.records[0].message
