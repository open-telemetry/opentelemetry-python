# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
import unittest
from unittest.mock import MagicMock, patch

from opentelemetry.sdk._configuration._instrumentation import (
    configure_instrumentation,
)
from opentelemetry.sdk._configuration.models import ExperimentalInstrumentation


def _make_ep(instrumentor_instance):
    """Build a fake entry point that returns ``instrumentor_instance`` when loaded."""
    ep = MagicMock()
    ep.load.return_value = MagicMock(return_value=instrumentor_instance)
    return ep


class TestConfigureInstrumentation(unittest.TestCase):
    def test_none_config_is_noop(self):
        # Must not raise.
        configure_instrumentation(None)

    def test_none_python_is_noop(self):
        configure_instrumentation(ExperimentalInstrumentation())

    @patch(
        "opentelemetry.sdk._configuration._instrumentation.entry_points",
        return_value=iter([]),
    )
    def test_unknown_instrumentor_logs_warning(self, _mock_eps):
        with self.assertLogs(
            "opentelemetry.sdk._configuration._instrumentation",
            level=logging.WARNING,
        ) as cm:
            configure_instrumentation(
                ExperimentalInstrumentation(python={"unknown_lib": {}})
            )
        self.assertTrue(
            any("unknown_lib" in msg for msg in cm.output),
            f"Expected warning mentioning 'unknown_lib', got: {cm.output}",
        )

    @patch("opentelemetry.sdk._configuration._instrumentation.entry_points")
    def test_instruments_listed_library_with_no_opts(self, mock_eps):
        instrumentor = MagicMock()
        mock_eps.return_value = iter([_make_ep(instrumentor)])

        configure_instrumentation(
            ExperimentalInstrumentation(python={"requests": {}})
        )

        mock_eps.assert_called_once_with(
            group="opentelemetry_instrumentor", name="requests"
        )
        instrumentor.instrument.assert_called_once_with()

    @patch("opentelemetry.sdk._configuration._instrumentation.entry_points")
    def test_forwards_kwargs_to_instrumentor(self, mock_eps):
        instrumentor = MagicMock()
        mock_eps.return_value = iter([_make_ep(instrumentor)])

        configure_instrumentation(
            ExperimentalInstrumentation(
                python={"flask": {"excluded_urls": "/healthz", "foo": "bar"}}
            )
        )

        instrumentor.instrument.assert_called_once_with(
            excluded_urls="/healthz", foo="bar"
        )

    @patch("opentelemetry.sdk._configuration._instrumentation.entry_points")
    def test_enabled_false_skips_instrumentation(self, mock_eps):
        instrumentor = MagicMock()
        mock_eps.return_value = iter([_make_ep(instrumentor)])

        configure_instrumentation(
            ExperimentalInstrumentation(
                python={"requests": {"enabled": False}}
            )
        )

        instrumentor.instrument.assert_not_called()

    @patch("opentelemetry.sdk._configuration._instrumentation.entry_points")
    def test_enabled_key_not_forwarded_to_instrumentor(self, mock_eps):
        instrumentor = MagicMock()
        mock_eps.return_value = iter([_make_ep(instrumentor)])

        configure_instrumentation(
            ExperimentalInstrumentation(
                python={"flask": {"enabled": True, "excluded_urls": "/ok"}}
            )
        )

        # "enabled" must be consumed, not forwarded.
        instrumentor.instrument.assert_called_once_with(excluded_urls="/ok")

    @patch("opentelemetry.sdk._configuration._instrumentation.entry_points")
    def test_multiple_instrumentors_all_called(self, mock_eps):
        flask_inst = MagicMock()
        requests_inst = MagicMock()

        def _side_effect(**kwargs):
            return iter([_make_ep(flask_inst if kwargs["name"] == "flask" else requests_inst)])

        mock_eps.side_effect = _side_effect

        configure_instrumentation(
            ExperimentalInstrumentation(
                python={"flask": {}, "requests": {"foo": "bar"}}
            )
        )

        flask_inst.instrument.assert_called_once_with()
        requests_inst.instrument.assert_called_once_with(foo="bar")

    @patch("opentelemetry.sdk._configuration._instrumentation.entry_points")
    def test_instrumentor_exception_does_not_stop_others(self, mock_eps):
        broken_inst = MagicMock()
        broken_inst.instrument.side_effect = RuntimeError("boom")
        ok_inst = MagicMock()

        call_count = 0

        def _side_effect(**_kwargs):
            nonlocal call_count
            call_count += 1
            return iter(
                [_make_ep(broken_inst if call_count == 1 else ok_inst)]
            )

        mock_eps.side_effect = _side_effect

        with self.assertLogs(
            "opentelemetry.sdk._configuration._instrumentation",
            level=logging.ERROR,
        ):
            configure_instrumentation(
                ExperimentalInstrumentation(
                    python={"broken": {}, "ok": {}}
                )
            )

        ok_inst.instrument.assert_called_once_with()
