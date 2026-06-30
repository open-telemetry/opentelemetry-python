# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import dataclasses
import logging
import unittest
from unittest.mock import MagicMock, patch

from opentelemetry.sdk._configuration._exceptions import ConfigurationError
from opentelemetry.sdk._configuration.instrumentation import (
    configure_instrumentation,
)
from opentelemetry.sdk._configuration.models import ExperimentalInstrumentation

_LOAD_EP = "opentelemetry.sdk._configuration.instrumentation.load_entry_point"


def _make_instrumentor_class(instance, config_dataclass=None):
    """Return a class mock whose constructor returns ``instance``."""
    cls = MagicMock(return_value=instance)
    cls.config_dataclass = config_dataclass
    return cls


class TestConfigureInstrumentation(unittest.TestCase):
    def test_none_config_is_noop(self):
        configure_instrumentation(None)

    def test_none_python_is_noop(self):
        configure_instrumentation(ExperimentalInstrumentation())

    @patch(_LOAD_EP, side_effect=ConfigurationError("not found"))
    def test_unknown_instrumentor_logs_warning(self, _mock_load):
        with self.assertLogs(
            "opentelemetry.sdk._configuration.instrumentation",
            level=logging.WARNING,
        ) as cm:
            configure_instrumentation(
                ExperimentalInstrumentation(python={"unknown_lib": {}})
            )
        self.assertTrue(
            any("unknown_lib" in msg for msg in cm.output),
            f"Expected warning mentioning 'unknown_lib', got: {cm.output}",
        )

    @patch(_LOAD_EP)
    def test_instruments_listed_library_with_no_opts(self, mock_load):
        instrumentor = MagicMock()
        mock_load.return_value = _make_instrumentor_class(instrumentor)

        configure_instrumentation(
            ExperimentalInstrumentation(python={"requests": {}})
        )

        mock_load.assert_called_once_with("opentelemetry_instrumentor", "requests")
        instrumentor.instrument.assert_called_once_with()

    @patch(_LOAD_EP)
    def test_forwards_kwargs_to_instrumentor_without_config_dataclass(self, mock_load):
        instrumentor = MagicMock()
        mock_load.return_value = _make_instrumentor_class(instrumentor)

        configure_instrumentation(
            ExperimentalInstrumentation(
                python={"flask": {"excluded_urls": "/healthz", "foo": "bar"}}
            )
        )

        instrumentor.instrument.assert_called_once_with(
            excluded_urls="/healthz", foo="bar"
        )

    @patch(_LOAD_EP)
    def test_enabled_false_skips_instrumentation(self, mock_load):
        instrumentor = MagicMock()
        mock_load.return_value = _make_instrumentor_class(instrumentor)

        configure_instrumentation(
            ExperimentalInstrumentation(
                python={"requests": {"enabled": False}}
            )
        )

        mock_load.assert_not_called()
        instrumentor.instrument.assert_not_called()

    @patch(_LOAD_EP)
    def test_enabled_key_not_forwarded_to_instrumentor(self, mock_load):
        instrumentor = MagicMock()
        mock_load.return_value = _make_instrumentor_class(instrumentor)

        configure_instrumentation(
            ExperimentalInstrumentation(
                python={"flask": {"enabled": True, "excluded_urls": "/ok"}}
            )
        )

        instrumentor.instrument.assert_called_once_with(excluded_urls="/ok")

    @patch(_LOAD_EP)
    def test_multiple_instrumentors_all_called(self, mock_load):
        flask_inst = MagicMock()
        requests_inst = MagicMock()

        def _side_effect(_group, name):
            return _make_instrumentor_class(
                flask_inst if name == "flask" else requests_inst
            )

        mock_load.side_effect = _side_effect

        configure_instrumentation(
            ExperimentalInstrumentation(
                python={"flask": {}, "requests": {"foo": "bar"}}
            )
        )

        flask_inst.instrument.assert_called_once_with()
        requests_inst.instrument.assert_called_once_with(foo="bar")

    @patch(_LOAD_EP)
    def test_instrumentor_exception_does_not_stop_others(self, mock_load):
        broken_inst = MagicMock()
        broken_inst.instrument.side_effect = RuntimeError("boom")
        ok_inst = MagicMock()

        call_count = 0

        def _side_effect(_group, _name):
            nonlocal call_count
            call_count += 1
            return _make_instrumentor_class(
                broken_inst if call_count == 1 else ok_inst
            )

        mock_load.side_effect = _side_effect

        with self.assertLogs(
            "opentelemetry.sdk._configuration.instrumentation",
            level=logging.ERROR,
        ):
            configure_instrumentation(
                ExperimentalInstrumentation(python={"broken": {}, "ok": {}})
            )

        ok_inst.instrument.assert_called_once_with()

    @patch(_LOAD_EP)
    def test_config_dataclass_coerces_opts(self, mock_load):
        @dataclasses.dataclass
        class RequestsConfig:
            excluded_urls: str | None = None
            capture_headers: bool | None = None

        instrumentor = MagicMock()
        mock_load.return_value = _make_instrumentor_class(
            instrumentor, config_dataclass=RequestsConfig
        )

        configure_instrumentation(
            ExperimentalInstrumentation(
                python={"requests": {"excluded_urls": "/health", "capture_headers": True}}
            )
        )

        instrumentor.instrument.assert_called_once_with(
            excluded_urls="/health", capture_headers=True
        )

    @patch(_LOAD_EP)
    def test_config_dataclass_none_fields_not_forwarded(self, mock_load):
        @dataclasses.dataclass
        class FlaskConfig:
            excluded_urls: str | None = None
            propagate_headers: bool | None = None

        instrumentor = MagicMock()
        mock_load.return_value = _make_instrumentor_class(
            instrumentor, config_dataclass=FlaskConfig
        )

        configure_instrumentation(
            ExperimentalInstrumentation(
                python={"flask": {"excluded_urls": "/ok"}}
            )
        )

        # propagate_headers was not set, so it must not appear in the call.
        instrumentor.instrument.assert_called_once_with(excluded_urls="/ok")

    @patch(_LOAD_EP)
    def test_config_dataclass_unknown_field_raises(self, mock_load):
        @dataclasses.dataclass
        class StrictConfig:
            excluded_urls: str | None = None

        instrumentor = MagicMock()
        mock_load.return_value = _make_instrumentor_class(
            instrumentor, config_dataclass=StrictConfig
        )

        with self.assertLogs(
            "opentelemetry.sdk._configuration.instrumentation",
            level=logging.ERROR,
        ):
            configure_instrumentation(
                ExperimentalInstrumentation(
                    python={"mylib": {"excluded_urls": "/ok", "typo_field": "bad"}}
                )
            )

        instrumentor.instrument.assert_not_called()
