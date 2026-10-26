# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import io
import logging
import unittest
from unittest.mock import MagicMock, patch

from opentelemetry._logs import NoOpLoggerProvider
from opentelemetry.configuration import (
    ConfigurationError,
    SdkComponents,
    configure_sdk,
    create_sdk,
    load_config,
)
from opentelemetry.configuration.models import (
    OpenTelemetryConfiguration,
    SeverityNumber,
)
from opentelemetry.configuration.models import (
    Propagator as PropagatorConfig,
)
from opentelemetry.configuration.models import (
    SimpleSpanProcessor as SimpleSpanProcessorConfig,
)
from opentelemetry.configuration.models import (
    SpanExporter as SpanExporterConfig,
)
from opentelemetry.configuration.models import (
    SpanProcessor as SpanProcessorConfig,
)
from opentelemetry.configuration.models import (
    TextMapPropagator as TextMapPropagatorConfig,
)
from opentelemetry.configuration.models import (
    TracerProvider as TracerProviderConfig,
)
from opentelemetry.metrics import NoOpMeterProvider
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.sdk.metrics import MeterProvider as SdkMeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider as SdkTracerProvider
from opentelemetry.trace import NoOpTracerProvider
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
)


def _config(**kwargs) -> OpenTelemetryConfiguration:
    return OpenTelemetryConfiguration(**{"file_format": "1.0", **kwargs})


def _tracer_provider_config() -> TracerProviderConfig:
    return TracerProviderConfig(
        processors=[SpanProcessorConfig(simple=SimpleSpanProcessorConfig(exporter=SpanExporterConfig(console={})))]
    )


def _tracecontext_propagator_config() -> PropagatorConfig:
    return PropagatorConfig(composite=[TextMapPropagatorConfig(tracecontext={})])


_TRACECONTEXT_FIELDS = TraceContextTextMapPropagator().fields


class _PatchedGlobalsTestCase(unittest.TestCase):
    """Replace the global setters used by ``_sdk`` with mocks."""

    def setUp(self):
        super().setUp()
        self.set_tracer_provider = self._start_patch("opentelemetry.configuration._sdk.trace.set_tracer_provider")
        self.set_meter_provider = self._start_patch("opentelemetry.configuration._sdk.metrics.set_meter_provider")
        self.set_logger_provider = self._start_patch("opentelemetry.configuration._sdk.set_logger_provider")
        self.set_global_textmap = self._start_patch("opentelemetry.configuration._sdk.set_global_textmap")
        self.configure_instrumentation = self._start_patch("opentelemetry.configuration._sdk.configure_instrumentation")

    def _start_patch(self, target: str) -> MagicMock:
        patcher = patch(target)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def assert_no_globals_set(self):
        self.set_tracer_provider.assert_not_called()
        self.set_meter_provider.assert_not_called()
        self.set_logger_provider.assert_not_called()
        self.set_global_textmap.assert_not_called()


class TestCreateSdk(_PatchedGlobalsTestCase):
    def test_does_not_set_globals(self):
        components = create_sdk(
            _config(
                tracer_provider=_tracer_provider_config(),
                propagator=_tracecontext_propagator_config(),
            )
        )
        self.addCleanup(components.shutdown)

        self.assertIsInstance(components.tracer_provider, SdkTracerProvider)
        self.assert_no_globals_set()
        self.configure_instrumentation.assert_not_called()

    def test_omitted_sections_return_noop_components(self):
        components = create_sdk(_config())

        self.assertIsInstance(components.tracer_provider, NoOpTracerProvider)
        self.assertIsInstance(components.meter_provider, NoOpMeterProvider)
        self.assertIsInstance(components.logger_provider, NoOpLoggerProvider)
        self.assertIsInstance(components.propagator, CompositePropagator)
        self.assertEqual(components.propagator.fields, set())
        self.assertIsInstance(components.resource, Resource)

    # pylint: disable=no-self-use
    def test_providers_share_resource(self):
        tracer_provider_config = _tracer_provider_config()
        with patch("opentelemetry.configuration._sdk.create_tracer_provider") as mock_create:
            components = create_sdk(_config(tracer_provider=tracer_provider_config))

        mock_create.assert_called_once_with(
            tracer_provider_config,
            components.resource,
            None,
            meter_provider=components.meter_provider,
        )

    def test_meter_provider_threaded_to_other_providers(self):
        created_meter_provider = MagicMock(spec=SdkMeterProvider)
        with (
            patch(
                "opentelemetry.configuration._sdk.create_meter_provider",
                return_value=created_meter_provider,
            ),
            patch("opentelemetry.configuration._sdk.create_tracer_provider") as mock_tracer,
            patch("opentelemetry.configuration._sdk.create_logger_provider") as mock_logger,
        ):
            create_sdk(
                _config(
                    tracer_provider=_tracer_provider_config(),
                    meter_provider=MagicMock(),
                    logger_provider=MagicMock(),
                )
            )

        self.assertIs(mock_tracer.call_args.kwargs["meter_provider"], created_meter_provider)
        self.assertIs(mock_logger.call_args.kwargs["meter_provider"], created_meter_provider)

    def test_disabled_returns_noop_providers_with_configured_propagator(self):
        with self.assertLogs("opentelemetry.configuration._sdk", level="WARNING"):
            components = create_sdk(
                _config(
                    disabled=True,
                    tracer_provider=_tracer_provider_config(),
                    propagator=_tracecontext_propagator_config(),
                )
            )

        self.assertIsInstance(components.tracer_provider, NoOpTracerProvider)
        self.assertIsInstance(components.meter_provider, NoOpMeterProvider)
        self.assertIsInstance(components.logger_provider, NoOpLoggerProvider)
        self.assertEqual(components.propagator.fields, _TRACECONTEXT_FIELDS)

    def test_failure_shuts_down_created_providers(self):
        created_meter_provider = MagicMock(spec=SdkMeterProvider)
        created_tracer_provider = MagicMock(spec=SdkTracerProvider)
        with (
            patch(
                "opentelemetry.configuration._sdk.create_meter_provider",
                return_value=created_meter_provider,
            ),
            patch(
                "opentelemetry.configuration._sdk.create_tracer_provider",
                return_value=created_tracer_provider,
            ),
            patch(
                "opentelemetry.configuration._sdk.create_logger_provider",
                side_effect=ConfigurationError("boom"),
            ),
        ):
            with self.assertRaises(ConfigurationError) as ctx:
                create_sdk(
                    _config(
                        tracer_provider=_tracer_provider_config(),
                        meter_provider=MagicMock(),
                        logger_provider=MagicMock(),
                    )
                )

        self.assertEqual(str(ctx.exception), "boom")
        created_meter_provider.shutdown.assert_called_once_with()
        created_tracer_provider.shutdown.assert_called_once_with()

    def test_failure_during_cleanup_still_raises_original_error(self):
        created_tracer_provider = MagicMock(spec=SdkTracerProvider)
        created_tracer_provider.shutdown.side_effect = RuntimeError("shutdown failed")
        with (
            patch(
                "opentelemetry.configuration._sdk.create_tracer_provider",
                return_value=created_tracer_provider,
            ),
            patch(
                "opentelemetry.configuration._sdk.create_logger_provider",
                side_effect=ConfigurationError("boom"),
            ),
        ):
            with self.assertLogs("opentelemetry.configuration._sdk", level="ERROR"):
                with self.assertRaises(ConfigurationError):
                    create_sdk(
                        _config(
                            tracer_provider=_tracer_provider_config(),
                            logger_provider=MagicMock(),
                        )
                    )

    def test_invalid_file_format_raises(self):
        for file_format in ("2.0", "not-a-version", None):
            with self.subTest(file_format=file_format):
                with self.assertRaises(ConfigurationError):
                    create_sdk(OpenTelemetryConfiguration(file_format=file_format))


class TestSdkComponentsShutdown(unittest.TestCase):
    # pylint: disable=no-self-use
    def test_shuts_down_sdk_providers_and_skips_noop(self):
        tracer_provider = MagicMock(spec=SdkTracerProvider)
        components = SdkComponents(
            tracer_provider=tracer_provider,
            meter_provider=NoOpMeterProvider(),
            logger_provider=NoOpLoggerProvider(),
            propagator=CompositePropagator([]),
            resource=Resource.get_empty(),
        )

        components.shutdown()

        tracer_provider.shutdown.assert_called_once_with()


class TestConfigureSdk(_PatchedGlobalsTestCase):
    def test_sets_all_globals(self):
        components = configure_sdk(_config(tracer_provider=_tracer_provider_config()))
        self.addCleanup(components.shutdown)

        self.assertIsInstance(components.tracer_provider, SdkTracerProvider)
        self.set_tracer_provider.assert_called_once_with(components.tracer_provider)
        self.set_meter_provider.assert_called_once_with(components.meter_provider)
        self.set_logger_provider.assert_called_once_with(components.logger_provider)
        self.set_global_textmap.assert_called_once_with(components.propagator)

    def test_omitted_sections_set_noop_globals(self):
        configure_sdk(_config())

        self.assertIsInstance(self.set_tracer_provider.call_args.args[0], NoOpTracerProvider)
        self.assertIsInstance(self.set_meter_provider.call_args.args[0], NoOpMeterProvider)
        self.assertIsInstance(self.set_logger_provider.call_args.args[0], NoOpLoggerProvider)
        self.assertEqual(self.set_global_textmap.call_args.args[0].fields, set())

    def test_configures_from_parsed_file(self):
        config = load_config(
            io.StringIO(
                'file_format: "1.0"\n'
                "tracer_provider:\n"
                "  processors:\n"
                "    - simple:\n"
                "        exporter:\n"
                "          console:\n"
            ),
            file_format="yaml",
        )

        components = configure_sdk(config)
        self.addCleanup(components.shutdown)

        self.assertIsInstance(components.tracer_provider, SdkTracerProvider)
        self.set_tracer_provider.assert_called_once_with(components.tracer_provider)

    def test_no_globals_set_on_create_failure(self):
        with patch(
            "opentelemetry.configuration._sdk.create_propagator",
            side_effect=ConfigurationError("boom"),
        ):
            with self.assertRaises(ConfigurationError):
                configure_sdk(_config(tracer_provider=_tracer_provider_config()))

        self.assert_no_globals_set()
        self.configure_instrumentation.assert_not_called()

    def test_no_globals_set_on_invalid_file_format(self):
        with self.assertRaises(ConfigurationError):
            configure_sdk(OpenTelemetryConfiguration(file_format="2.0"))

        self.assert_no_globals_set()

    def test_disabled_sets_noop_globals_and_configured_propagator(self):
        with self.assertLogs("opentelemetry.configuration._sdk", level="WARNING"):
            configure_sdk(
                _config(
                    disabled=True,
                    tracer_provider=_tracer_provider_config(),
                    propagator=_tracecontext_propagator_config(),
                )
            )

        self.assertIsInstance(self.set_tracer_provider.call_args.args[0], NoOpTracerProvider)
        self.assertIsInstance(self.set_meter_provider.call_args.args[0], NoOpMeterProvider)
        self.assertIsInstance(self.set_logger_provider.call_args.args[0], NoOpLoggerProvider)
        self.assertEqual(self.set_global_textmap.call_args.args[0].fields, _TRACECONTEXT_FIELDS)
        self.configure_instrumentation.assert_not_called()

    def test_configures_instrumentation_when_enabled(self):
        configure_sdk(_config())

        self.configure_instrumentation.assert_called_once_with(None)


class TestConfigureSdkLogLevel(_PatchedGlobalsTestCase):
    def setUp(self):
        super().setUp()
        # Preserve whatever level was set before this test so we can
        # restore it afterwards, keeping tests isolated from each other
        # and from the ambient logging configuration.
        original_level = logging.getLogger("opentelemetry").level
        self.addCleanup(logging.getLogger("opentelemetry").setLevel, original_level)

    def test_severity_number_variants_map_correctly(self):
        cases = {
            logging.DEBUG: ["trace", "trace2", "trace3", "trace4", "debug", "debug2", "debug3", "debug4"],
            logging.INFO: ["info", "info2", "info3", "info4"],
            logging.WARNING: ["warn", "warn2", "warn3", "warn4"],
            logging.ERROR: ["error", "error2", "error3", "error4"],
            logging.CRITICAL: ["fatal", "fatal2", "fatal3", "fatal4"],
        }
        for expected_level, severities in cases.items():
            for severity in severities:
                with self.subTest(severity=severity):
                    configure_sdk(_config(log_level=SeverityNumber(severity)))
                    self.assertEqual(logging.getLogger("opentelemetry").level, expected_level)

    def test_absent_log_level_leaves_logger_unchanged(self):
        logging.getLogger("opentelemetry").setLevel(logging.ERROR)
        configure_sdk(_config())
        self.assertEqual(logging.getLogger("opentelemetry").level, logging.ERROR)

    def test_log_level_applied_when_disabled(self):
        logging.getLogger("opentelemetry").setLevel(logging.WARNING)
        with self.assertLogs("opentelemetry.configuration._sdk", level="WARNING"):
            configure_sdk(_config(disabled=True, log_level=SeverityNumber.error))
        self.assertEqual(logging.getLogger("opentelemetry").level, logging.ERROR)

    def test_log_level_not_applied_on_failure(self):
        logging.getLogger("opentelemetry").setLevel(logging.WARNING)
        with patch(
            "opentelemetry.configuration._sdk.create_propagator",
            side_effect=ConfigurationError("boom"),
        ):
            with self.assertRaises(ConfigurationError):
                configure_sdk(_config(log_level=SeverityNumber.error))
        self.assertEqual(logging.getLogger("opentelemetry").level, logging.WARNING)
