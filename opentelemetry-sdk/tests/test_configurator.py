# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# type: ignore
# pylint: skip-file

from logging import WARNING, getLogger
from os import environ
from typing import Dict, Iterable, Optional, Sequence
from unittest import TestCase, mock
from unittest.mock import Mock, patch

from pytest import raises

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.environment_variables import OTEL_PYTHON_ID_GENERATOR
from opentelemetry.sdk._configuration import (
    _EXPORTER_OTLP,
    _EXPORTER_OTLP_PROTO_GRPC,
    _EXPORTER_OTLP_PROTO_HTTP,
    _get_exporter_names,
    _get_id_generator,
    _get_sampler,
    _import_config_components,
    _import_exporters,
    _import_id_generator,
    _import_sampler,
    _init_logging,
    _init_metrics,
    _init_tracing,
    _initialize_components,
    _OTelSDKConfigurator,
)
from opentelemetry.sdk._logs import LoggingHandler
from opentelemetry.sdk._logs.export import ConsoleLogExporter
from opentelemetry.sdk.environment_variables import (
    OTEL_TRACES_SAMPLER,
    OTEL_TRACES_SAMPLER_ARG,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    ConsoleMetricExporter,
    Metric,
    MetricExporter,
    MetricReader,
)
from opentelemetry.sdk.metrics.view import Aggregation
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.sdk.trace.id_generator import IdGenerator, RandomIdGenerator
from opentelemetry.sdk.trace.sampling import (
    ALWAYS_ON,
    Decision,
    ParentBased,
    Sampler,
    SamplingResult,
    TraceIdRatioBased,
)
from opentelemetry.trace import Link, SpanKind
from opentelemetry.trace.span import TraceState
from opentelemetry.util.types import Attributes


class Provider:
    def __init__(self, resource=None, sampler=None, id_generator=None):
        self.sampler = sampler
        self.id_generator = id_generator
        self.processor = None
        self.resource = resource or Resource.create({})

    def add_span_processor(self, processor):
        self.processor = processor


class DummyLoggerProvider:
    def __init__(self, resource=None):
        self.resource = resource
        self.processor = DummyLogRecordProcessor(DummyOTLPLogExporter())

    def add_log_record_processor(self, processor):
        self.processor = processor

    def get_logger(self, name, *args, **kwargs):
        return DummyLogger(name, self.resource, self.processor)

    def force_flush(self, *args, **kwargs):
        pass


class DummyMeterProvider(MeterProvider):
    pass


class DummyLogger:
    def __init__(self, name, resource, processor):
        self.name = name
        self.resource = resource
        self.processor = processor

    def emit(self, record):
        self.processor.emit(record)


class DummyLogRecordProcessor:
    def __init__(self, exporter):
        self.exporter = exporter

    def emit(self, record):
        self.exporter.export([record])

    def force_flush(self, time):
        pass

    def shutdown(self):
        pass


class Processor:
    def __init__(self, exporter):
        self.exporter = exporter


class DummyMetricReader(MetricReader):
    def __init__(
        self,
        exporter: MetricExporter,
        preferred_temporality: Dict[type, AggregationTemporality] = None,
        preferred_aggregation: Dict[type, Aggregation] = None,
        export_interval_millis: Optional[float] = None,
        export_timeout_millis: Optional[float] = None,
    ) -> None:
        super().__init__(
            preferred_temporality=preferred_temporality,
            preferred_aggregation=preferred_aggregation,
        )
        self.exporter = exporter

    def _receive_metrics(
        self,
        metrics: Iterable[Metric],
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> None:
        self.exporter.export(None)

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        return True


# MetricReader that can be configured as a pull exporter
class DummyMetricReaderPullExporter(MetricReader):
    def _receive_metrics(
        self,
        metrics: Iterable[Metric],
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> None:
        pass

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        return True


class DummyOTLPMetricExporter:
    def __init__(self, *args, **kwargs):
        self.export_called = False

    def export(self, batch):
        self.export_called = True

    def shutdown(self):
        pass


class Exporter:
    def __init__(self):
        tracer_provider = trace.get_tracer_provider()
        self.service_name = (
            tracer_provider.resource.attributes[SERVICE_NAME]
            if getattr(tracer_provider, "resource", None)
            else Resource.create().attributes.get(SERVICE_NAME)
        )

    def shutdown(self):
        pass


class OTLPSpanExporter:
    pass


class DummyOTLPLogExporter:
    def __init__(self, *args, **kwargs):
        self.export_called = False

    def export(self, batch):
        self.export_called = True

    def shutdown(self):
        pass


class CustomSampler(Sampler):
    def __init__(self) -> None:
        pass

    def get_description(self) -> str:
        return "CustomSampler"

    def should_sample(
        self,
        parent_context: Optional["Context"],
        trace_id: int,
        name: str,
        kind: SpanKind = None,
        attributes: Attributes = None,
        links: Sequence[Link] = None,
        trace_state: TraceState = None,
    ) -> "SamplingResult":
        return SamplingResult(
            Decision.RECORD_AND_SAMPLE,
            None,
            None,
        )


class CustomRatioSampler(TraceIdRatioBased):
    def __init__(self, ratio):
        if not isinstance(ratio, float):
            raise ValueError(
                "CustomRatioSampler ratio argument is not a float."
            )
        self.ratio = ratio
        super().__init__(ratio)

    def get_description(self) -> str:
        return "CustomSampler"

    def should_sample(
        self,
        parent_context: Optional["Context"],
        trace_id: int,
        name: str,
        kind: SpanKind = None,
        attributes: Attributes = None,
        links: Sequence[Link] = None,
        trace_state: TraceState = None,
    ) -> "SamplingResult":
        return SamplingResult(
            Decision.RECORD_AND_SAMPLE,
            None,
            None,
        )


class CustomSamplerFactory:
    @staticmethod
    def get_custom_sampler(unused_sampler_arg):
        return CustomSampler()

    @staticmethod
    def get_custom_ratio_sampler(sampler_arg):
        return CustomRatioSampler(float(sampler_arg))

    @staticmethod
    def empty_get_custom_sampler(sampler_arg):
        return


class CustomIdGenerator(IdGenerator):
    def generate_span_id(self):
        pass

    def generate_trace_id(self):
        pass


class IterEntryPoint:
    def __init__(self, name, class_type):
        self.name = name
        self.class_type = class_type

    def load(self):
        return self.class_type


class TestTraceInit(TestCase):
    def setUp(self):
        super()
        self.get_provider_patcher = patch(
            "opentelemetry.sdk._configuration.TracerProvider", Provider
        )
        self.get_processor_patcher = patch(
            "opentelemetry.sdk._configuration.BatchSpanProcessor", Processor
        )
        self.set_provider_patcher = patch(
            "opentelemetry.sdk._configuration.set_tracer_provider"
        )

        self.get_provider_mock = self.get_provider_patcher.start()
        self.get_processor_mock = self.get_processor_patcher.start()
        self.set_provider_mock = self.set_provider_patcher.start()

    def tearDown(self):
        super()
        self.get_provider_patcher.stop()
        self.get_processor_patcher.stop()
        self.set_provider_patcher.stop()

    # pylint: disable=protected-access
    @patch.dict(
        environ, {"OTEL_RESOURCE_ATTRIBUTES": "service.name=my-test-service"}
    )
    def test_trace_init_default(self):
        auto_resource = Resource.create(
            {
                "telemetry.auto.version": "test-version",
            }
        )
        _init_tracing(
            {"zipkin": Exporter},
            id_generator=RandomIdGenerator(),
            resource=auto_resource,
        )

        self.assertEqual(self.set_provider_mock.call_count, 1)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsInstance(provider, Provider)
        self.assertIsInstance(provider.id_generator, RandomIdGenerator)
        self.assertIsInstance(provider.processor, Processor)
        self.assertIsInstance(provider.processor.exporter, Exporter)
        self.assertEqual(
            provider.processor.exporter.service_name, "my-test-service"
        )
        self.assertEqual(
            provider.resource.attributes.get("telemetry.auto.version"),
            "test-version",
        )

    @patch.dict(
        environ,
        {"OTEL_RESOURCE_ATTRIBUTES": "service.name=my-otlp-test-service"},
    )
    def test_trace_init_otlp(self):
        _init_tracing(
            {"otlp": OTLPSpanExporter}, id_generator=RandomIdGenerator()
        )

        self.assertEqual(self.set_provider_mock.call_count, 1)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsInstance(provider, Provider)
        self.assertIsInstance(provider.id_generator, RandomIdGenerator)
        self.assertIsInstance(provider.processor, Processor)
        self.assertIsInstance(provider.processor.exporter, OTLPSpanExporter)
        self.assertIsInstance(provider.resource, Resource)
        self.assertEqual(
            provider.resource.attributes.get("service.name"),
            "my-otlp-test-service",
        )

    @patch.dict(environ, {OTEL_PYTHON_ID_GENERATOR: "custom_id_generator"})
    @patch("opentelemetry.sdk._configuration.IdGenerator", new=IdGenerator)
    @patch("opentelemetry.sdk._configuration.entry_points")
    def test_trace_init_custom_id_generator(self, mock_entry_points):
        mock_entry_points.configure_mock(
            return_value=[
                IterEntryPoint("custom_id_generator", CustomIdGenerator)
            ]
        )

        id_generator_name = _get_id_generator()
        id_generator = _import_id_generator(id_generator_name)
        _init_tracing({}, id_generator=id_generator)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsInstance(provider.id_generator, CustomIdGenerator)

    @patch.dict(
        "os.environ", {OTEL_TRACES_SAMPLER: "non_existent_entry_point"}
    )
    def test_trace_init_custom_sampler_with_env_non_existent_entry_point(self):
        sampler_name = _get_sampler()
        with self.assertLogs(level=WARNING):
            sampler = _import_sampler(sampler_name)
        _init_tracing({}, sampler=sampler)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsNone(provider.sampler)

    @patch("opentelemetry.sdk._configuration.entry_points")
    @patch.dict("os.environ", {OTEL_TRACES_SAMPLER: "custom_sampler_factory"})
    def test_trace_init_custom_sampler_with_env(self, mock_entry_points):
        mock_entry_points.configure_mock(
            return_value=[
                IterEntryPoint(
                    "custom_sampler_factory",
                    CustomSamplerFactory.get_custom_sampler,
                )
            ]
        )

        sampler_name = _get_sampler()
        sampler = _import_sampler(sampler_name)
        _init_tracing({}, sampler=sampler)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsInstance(provider.sampler, CustomSampler)

    @patch("opentelemetry.sdk._configuration.entry_points")
    @patch.dict("os.environ", {OTEL_TRACES_SAMPLER: "custom_sampler_factory"})
    def test_trace_init_custom_sampler_with_env_bad_factory(
        self, mock_entry_points
    ):
        mock_entry_points.configure_mock(
            return_value=[
                IterEntryPoint(
                    "custom_sampler_factory",
                    CustomSamplerFactory.empty_get_custom_sampler,
                )
            ]
        )

        sampler_name = _get_sampler()
        with self.assertLogs(level=WARNING):
            sampler = _import_sampler(sampler_name)
        _init_tracing({}, sampler=sampler)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsNone(provider.sampler)

    @patch("opentelemetry.sdk._configuration.entry_points")
    @patch.dict(
        "os.environ",
        {
            OTEL_TRACES_SAMPLER: "custom_sampler_factory",
            OTEL_TRACES_SAMPLER_ARG: "0.5",
        },
    )
    def test_trace_init_custom_sampler_with_env_unused_arg(
        self, mock_entry_points
    ):
        mock_entry_points.configure_mock(
            return_value=[
                IterEntryPoint(
                    "custom_sampler_factory",
                    CustomSamplerFactory.get_custom_sampler,
                )
            ]
        )

        sampler_name = _get_sampler()
        sampler = _import_sampler(sampler_name)
        _init_tracing({}, sampler=sampler)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsInstance(provider.sampler, CustomSampler)

    @patch("opentelemetry.sdk._configuration.entry_points")
    @patch.dict(
        "os.environ",
        {
            OTEL_TRACES_SAMPLER: "custom_ratio_sampler_factory",
            OTEL_TRACES_SAMPLER_ARG: "0.5",
        },
    )
    def test_trace_init_custom_ratio_sampler_with_env(self, mock_entry_points):
        mock_entry_points.configure_mock(
            return_value=[
                IterEntryPoint(
                    "custom_ratio_sampler_factory",
                    CustomSamplerFactory.get_custom_ratio_sampler,
                )
            ]
        )

        sampler_name = _get_sampler()
        sampler = _import_sampler(sampler_name)
        _init_tracing({}, sampler=sampler)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsInstance(provider.sampler, CustomRatioSampler)
        self.assertEqual(provider.sampler.ratio, 0.5)

    @patch("opentelemetry.sdk._configuration.entry_points")
    @patch.dict(
        "os.environ",
        {
            OTEL_TRACES_SAMPLER: "custom_ratio_sampler_factory",
            OTEL_TRACES_SAMPLER_ARG: "foobar",
        },
    )
    def test_trace_init_custom_ratio_sampler_with_env_bad_arg(
        self, mock_entry_points
    ):
        mock_entry_points.configure_mock(
            return_value=[
                IterEntryPoint(
                    "custom_ratio_sampler_factory",
                    CustomSamplerFactory.get_custom_ratio_sampler,
                )
            ]
        )

        sampler_name = _get_sampler()
        with self.assertLogs(level=WARNING):
            sampler = _import_sampler(sampler_name)
        _init_tracing({}, sampler=sampler)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsNone(provider.sampler)

    @patch("opentelemetry.sdk._configuration.entry_points")
    @patch.dict(
        "os.environ",
        {
            OTEL_TRACES_SAMPLER: "custom_ratio_sampler_factory",
        },
    )
    def test_trace_init_custom_ratio_sampler_with_env_missing_arg(
        self, mock_entry_points
    ):
        mock_entry_points.configure_mock(
            return_value=[
                IterEntryPoint(
                    "custom_ratio_sampler_factory",
                    CustomSamplerFactory.get_custom_ratio_sampler,
                )
            ]
        )

        sampler_name = _get_sampler()
        with self.assertLogs(level=WARNING):
            sampler = _import_sampler(sampler_name)
        _init_tracing({}, sampler=sampler)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsNone(provider.sampler)

    @patch("opentelemetry.sdk._configuration.entry_points")
    @patch.dict(
        "os.environ",
        {
            OTEL_TRACES_SAMPLER: "custom_sampler_factory",
            OTEL_TRACES_SAMPLER_ARG: "0.5",
        },
    )
    def test_trace_init_custom_ratio_sampler_with_env_multiple_entry_points(
        self, mock_entry_points
    ):
        mock_entry_points.configure_mock(
            return_value=[
                IterEntryPoint(
                    "custom_sampler_factory",
                    CustomSamplerFactory.get_custom_sampler,
                ),
            ]
        )

        sampler_name = _get_sampler()
        sampler = _import_sampler(sampler_name)
        _init_tracing({}, sampler=sampler)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsInstance(provider.sampler, CustomSampler)

    def verify_default_sampler(self, tracer_provider):
        self.assertIsInstance(tracer_provider.sampler, ParentBased)
        # pylint: disable=protected-access
        self.assertEqual(tracer_provider.sampler._root, ALWAYS_ON)


class TestLoggingInit(TestCase):
    def setUp(self):
        self.processor_patch = patch(
            "opentelemetry.sdk._configuration.BatchLogRecordProcessor",
            DummyLogRecordProcessor,
        )
        self.provider_patch = patch(
            "opentelemetry.sdk._configuration.LoggerProvider",
            DummyLoggerProvider,
        )
        self.set_provider_patch = patch(
            "opentelemetry.sdk._configuration.set_logger_provider"
        )

        self.event_logger_provider_instance_mock = Mock()
        self.event_logger_provider_patch = patch(
            "opentelemetry.sdk._configuration.EventLoggerProvider",
            return_value=self.event_logger_provider_instance_mock,
        )
        self.set_event_logger_provider_patch = patch(
            "opentelemetry.sdk._configuration.set_event_logger_provider"
        )

        self.processor_mock = self.processor_patch.start()
        self.provider_mock = self.provider_patch.start()
        self.set_provider_mock = self.set_provider_patch.start()

        self.event_logger_provider_mock = (
            self.event_logger_provider_patch.start()
        )
        self.set_event_logger_provider_mock = (
            self.set_event_logger_provider_patch.start()
        )

    def tearDown(self):
        self.processor_patch.stop()
        self.set_provider_patch.stop()
        self.provider_patch.stop()
        self.event_logger_provider_patch.stop()
        self.set_event_logger_provider_patch.stop()
        root_logger = getLogger("root")
        root_logger.handlers = [
            handler
            for handler in root_logger.handlers
            if not isinstance(handler, LoggingHandler)
        ]

    def test_logging_init_empty(self):
        auto_resource = Resource.create(
            {
                "telemetry.auto.version": "auto-version",
            }
        )
        _init_logging({}, resource=auto_resource)
        self.assertEqual(self.set_provider_mock.call_count, 1)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsInstance(provider, DummyLoggerProvider)
        self.assertIsInstance(provider.resource, Resource)
        self.assertEqual(
            provider.resource.attributes.get("telemetry.auto.version"),
            "auto-version",
        )
        self.event_logger_provider_mock.assert_called_once_with(
            logger_provider=provider
        )
        self.set_event_logger_provider_mock.assert_called_once_with(
            self.event_logger_provider_instance_mock
        )

    @patch.dict(
        environ,
        {"OTEL_RESOURCE_ATTRIBUTES": "service.name=otlp-service"},
    )
    def test_logging_init_exporter(self):
        resource = Resource.create({})
        _init_logging({"otlp": DummyOTLPLogExporter}, resource=resource)
        self.assertEqual(self.set_provider_mock.call_count, 1)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsInstance(provider, DummyLoggerProvider)
        self.assertIsInstance(provider.resource, Resource)
        self.assertEqual(
            provider.resource.attributes.get("service.name"),
            "otlp-service",
        )
        self.assertIsInstance(provider.processor, DummyLogRecordProcessor)
        self.assertIsInstance(
            provider.processor.exporter, DummyOTLPLogExporter
        )
        getLogger(__name__).error("hello")
        self.assertTrue(provider.processor.exporter.export_called)

    @patch.dict(
        environ,
        {"OTEL_RESOURCE_ATTRIBUTES": "service.name=otlp-service"},
    )
    def test_logging_init_exporter_without_handler_setup(self):
        resource = Resource.create({})
        _init_logging(
            {"otlp": DummyOTLPLogExporter},
            resource=resource,
            setup_logging_handler=False,
        )
        self.assertEqual(self.set_provider_mock.call_count, 1)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsInstance(provider, DummyLoggerProvider)
        self.assertIsInstance(provider.resource, Resource)
        self.assertEqual(
            provider.resource.attributes.get("service.name"),
            "otlp-service",
        )
        self.assertIsInstance(provider.processor, DummyLogRecordProcessor)
        self.assertIsInstance(
            provider.processor.exporter, DummyOTLPLogExporter
        )
        getLogger(__name__).error("hello")
        self.assertFalse(provider.processor.exporter.export_called)

    @patch.dict(
        environ,
        {"OTEL_RESOURCE_ATTRIBUTES": "service.name=otlp-service"},
    )
    @patch("opentelemetry.sdk._configuration._init_tracing")
    @patch("opentelemetry.sdk._configuration._init_logging")
    def test_logging_init_disable_default(self, logging_mock, tracing_mock):
        _initialize_components(auto_instrumentation_version="auto-version")
        self.assertEqual(tracing_mock.call_count, 1)
        logging_mock.assert_called_once_with(mock.ANY, mock.ANY, False)

    @patch.dict(
        environ,
        {
            "OTEL_RESOURCE_ATTRIBUTES": "service.name=otlp-service",
            "OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED": "True",
        },
    )
    @patch("opentelemetry.sdk._configuration._init_tracing")
    @patch("opentelemetry.sdk._configuration._init_logging")
    def test_logging_init_enable_env(self, logging_mock, tracing_mock):
        with self.assertLogs(level=WARNING):
            _initialize_components(auto_instrumentation_version="auto-version")
        logging_mock.assert_called_once_with(mock.ANY, mock.ANY, True)
        self.assertEqual(tracing_mock.call_count, 1)

    @patch.dict(
        environ,
        {
            "OTEL_RESOURCE_ATTRIBUTES": "service.name=otlp-service",
            "OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED": "True",
        },
    )
    @patch("opentelemetry.sdk._configuration._init_tracing")
    @patch("opentelemetry.sdk._configuration._init_logging")
    @patch("opentelemetry.sdk._configuration._init_metrics")
    def test_initialize_components_resource(
        self, metrics_mock, logging_mock, tracing_mock
    ):
        _initialize_components(auto_instrumentation_version="auto-version")
        self.assertEqual(logging_mock.call_count, 1)
        self.assertEqual(tracing_mock.call_count, 1)
        self.assertEqual(metrics_mock.call_count, 1)

        _, args, _ = logging_mock.mock_calls[0]
        logging_resource = args[1]
        _, _, kwargs = tracing_mock.mock_calls[0]
        tracing_resource = kwargs["resource"]
        _, args, _ = metrics_mock.mock_calls[0]
        metrics_resource = args[1]
        self.assertEqual(logging_resource, tracing_resource)
        self.assertEqual(logging_resource, metrics_resource)
        self.assertEqual(tracing_resource, metrics_resource)

    @patch.dict(
        environ,
        {
            "OTEL_TRACES_EXPORTER": _EXPORTER_OTLP,
            "OTEL_METRICS_EXPORTER": _EXPORTER_OTLP_PROTO_GRPC,
            "OTEL_LOGS_EXPORTER": _EXPORTER_OTLP_PROTO_HTTP,
        },
    )
    @patch.dict(
        environ,
        {
            "OTEL_RESOURCE_ATTRIBUTES": "service.name=otlp-service, custom.key.1=env-value",
            "OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED": "False",
        },
    )
    @patch("opentelemetry.sdk._configuration.Resource")
    @patch("opentelemetry.sdk._configuration._import_exporters")
    @patch("opentelemetry.sdk._configuration._get_exporter_names")
    @patch("opentelemetry.sdk._configuration._init_tracing")
    @patch("opentelemetry.sdk._configuration._init_logging")
    @patch("opentelemetry.sdk._configuration._init_metrics")
    def test_initialize_components_kwargs(
        self,
        metrics_mock,
        logging_mock,
        tracing_mock,
        exporter_names_mock,
        import_exporters_mock,
        resource_mock,
    ):
        exporter_names_mock.return_value = [
            "env_var_exporter_1",
            "env_var_exporter_2",
        ]
        import_exporters_mock.return_value = (
            "TEST_SPAN_EXPORTERS_DICT",
            "TEST_METRICS_EXPORTERS_DICT",
            "TEST_LOG_EXPORTERS_DICT",
        )
        resource_mock.create.return_value = "TEST_RESOURCE"
        kwargs = {
            "auto_instrumentation_version": "auto-version",
            "trace_exporter_names": ["custom_span_exporter"],
            "metric_exporter_names": ["custom_metric_exporter"],
            "log_exporter_names": ["custom_log_exporter"],
            "sampler": "TEST_SAMPLER",
            "resource_attributes": {
                "custom.key.1": "pass-in-value-1",
                "custom.key.2": "pass-in-value-2",
            },
            "id_generator": "TEST_GENERATOR",
            "setup_logging_handler": True,
        }
        _initialize_components(**kwargs)

        import_exporters_mock.assert_called_once_with(
            [
                "custom_span_exporter",
                "env_var_exporter_1",
                "env_var_exporter_2",
            ],
            [
                "custom_metric_exporter",
                "env_var_exporter_1",
                "env_var_exporter_2",
            ],
            [
                "custom_log_exporter",
                "env_var_exporter_1",
                "env_var_exporter_2",
            ],
        )
        resource_mock.create.assert_called_once_with(
            {
                "telemetry.auto.version": "auto-version",
                "custom.key.1": "pass-in-value-1",
                "custom.key.2": "pass-in-value-2",
            }
        )
        # Resource is checked separates
        tracing_mock.assert_called_once_with(
            exporters="TEST_SPAN_EXPORTERS_DICT",
            id_generator="TEST_GENERATOR",
            sampler="TEST_SAMPLER",
            resource="TEST_RESOURCE",
        )
        metrics_mock.assert_called_once_with(
            "TEST_METRICS_EXPORTERS_DICT",
            "TEST_RESOURCE",
        )
        logging_mock.assert_called_once_with(
            "TEST_LOG_EXPORTERS_DICT",
            "TEST_RESOURCE",
            True,
        )


class TestMetricsInit(TestCase):
    def setUp(self):
        self.metric_reader_patch = patch(
            "opentelemetry.sdk._configuration.PeriodicExportingMetricReader",
            DummyMetricReader,
        )
        self.provider_patch = patch(
            "opentelemetry.sdk._configuration.MeterProvider",
            DummyMeterProvider,
        )
        self.set_provider_patch = patch(
            "opentelemetry.sdk._configuration.set_meter_provider"
        )

        self.metric_reader_mock = self.metric_reader_patch.start()
        self.provider_mock = self.provider_patch.start()
        self.set_provider_mock = self.set_provider_patch.start()

    def tearDown(self):
        self.metric_reader_patch.stop()
        self.set_provider_patch.stop()
        self.provider_patch.stop()

    def test_metrics_init_empty(self):
        auto_resource = Resource.create(
            {
                "telemetry.auto.version": "auto-version",
            }
        )
        _init_metrics({}, resource=auto_resource)
        self.assertEqual(self.set_provider_mock.call_count, 1)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsInstance(provider, DummyMeterProvider)
        self.assertIsInstance(provider._sdk_config.resource, Resource)
        self.assertEqual(
            provider._sdk_config.resource.attributes.get(
                "telemetry.auto.version"
            ),
            "auto-version",
        )

    @patch.dict(
        environ,
        {"OTEL_RESOURCE_ATTRIBUTES": "service.name=otlp-service"},
    )
    def test_metrics_init_exporter(self):
        resource = Resource.create({})
        _init_metrics({"otlp": DummyOTLPMetricExporter}, resource=resource)
        self.assertEqual(self.set_provider_mock.call_count, 1)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsInstance(provider, DummyMeterProvider)
        self.assertIsInstance(provider._sdk_config.resource, Resource)
        self.assertEqual(
            provider._sdk_config.resource.attributes.get("service.name"),
            "otlp-service",
        )
        reader = provider._sdk_config.metric_readers[0]
        self.assertIsInstance(reader, DummyMetricReader)
        self.assertIsInstance(reader.exporter, DummyOTLPMetricExporter)

    def test_metrics_init_pull_exporter(self):
        resource = Resource.create({})
        _init_metrics(
            {"dummy_metric_reader": DummyMetricReaderPullExporter},
            resource=resource,
        )
        self.assertEqual(self.set_provider_mock.call_count, 1)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsInstance(provider, DummyMeterProvider)
        reader = provider._sdk_config.metric_readers[0]
        self.assertIsInstance(reader, DummyMetricReaderPullExporter)


class TestExporterNames(TestCase):
    @patch.dict(
        environ,
        {
            "OTEL_TRACES_EXPORTER": _EXPORTER_OTLP,
            "OTEL_METRICS_EXPORTER": _EXPORTER_OTLP_PROTO_GRPC,
            "OTEL_LOGS_EXPORTER": _EXPORTER_OTLP_PROTO_HTTP,
        },
    )
    def test_otlp_exporter(self):
        self.assertEqual(
            _get_exporter_names("traces"), [_EXPORTER_OTLP_PROTO_GRPC]
        )
        self.assertEqual(
            _get_exporter_names("metrics"), [_EXPORTER_OTLP_PROTO_GRPC]
        )
        self.assertEqual(
            _get_exporter_names("logs"), [_EXPORTER_OTLP_PROTO_HTTP]
        )

    @patch.dict(
        environ,
        {
            "OTEL_TRACES_EXPORTER": _EXPORTER_OTLP,
            "OTEL_METRICS_EXPORTER": _EXPORTER_OTLP,
            "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
            "OTEL_EXPORTER_OTLP_METRICS_PROTOCOL": "grpc",
        },
    )
    def test_otlp_custom_exporter(self):
        self.assertEqual(
            _get_exporter_names("traces"), [_EXPORTER_OTLP_PROTO_HTTP]
        )
        self.assertEqual(
            _get_exporter_names("metrics"), [_EXPORTER_OTLP_PROTO_GRPC]
        )

    @patch.dict(
        environ,
        {
            "OTEL_TRACES_EXPORTER": _EXPORTER_OTLP_PROTO_HTTP,
            "OTEL_METRICS_EXPORTER": _EXPORTER_OTLP_PROTO_GRPC,
            "OTEL_EXPORTER_OTLP_PROTOCOL": "grpc",
            "OTEL_EXPORTER_OTLP_METRICS_PROTOCOL": "http/protobuf",
        },
    )
    def test_otlp_exporter_conflict(self):
        # Verify that OTEL_*_EXPORTER is used, and a warning is logged
        with self.assertLogs(level="WARNING") as logs_context:
            self.assertEqual(
                _get_exporter_names("traces"), [_EXPORTER_OTLP_PROTO_HTTP]
            )
        assert len(logs_context.output) == 1

        with self.assertLogs(level="WARNING") as logs_context:
            self.assertEqual(
                _get_exporter_names("metrics"), [_EXPORTER_OTLP_PROTO_GRPC]
            )
        assert len(logs_context.output) == 1

    @patch.dict(environ, {"OTEL_TRACES_EXPORTER": "zipkin"})
    def test_multiple_exporters(self):
        self.assertEqual(sorted(_get_exporter_names("traces")), ["zipkin"])

    @patch.dict(environ, {"OTEL_TRACES_EXPORTER": "none"})
    def test_none_exporters(self):
        self.assertEqual(sorted(_get_exporter_names("traces")), [])

    def test_no_exporters(self):
        self.assertEqual(sorted(_get_exporter_names("traces")), [])

    @patch.dict(environ, {"OTEL_TRACES_EXPORTER": ""})
    def test_empty_exporters(self):
        self.assertEqual(sorted(_get_exporter_names("traces")), [])


class TestImportExporters(TestCase):
    def test_console_exporters(self):
        trace_exporters, metric_exporterts, logs_exporters = _import_exporters(
            ["console"], ["console"], ["console"]
        )
        self.assertEqual(
            trace_exporters["console"].__class__, ConsoleSpanExporter.__class__
        )
        self.assertEqual(
            logs_exporters["console"].__class__, ConsoleLogExporter.__class__
        )
        self.assertEqual(
            metric_exporterts["console"].__class__,
            ConsoleMetricExporter.__class__,
        )

    @patch(
        "opentelemetry.sdk._configuration.entry_points",
    )
    def test_metric_pull_exporter(self, mock_entry_points: Mock):
        def mock_entry_points_impl(group, name):
            if name == "dummy_pull_exporter":
                return [
                    IterEntryPoint(
                        name=name, class_type=DummyMetricReaderPullExporter
                    )
                ]
            return []

        mock_entry_points.side_effect = mock_entry_points_impl
        _, metric_exporters, _ = _import_exporters(
            [], ["dummy_pull_exporter"], []
        )
        self.assertIs(
            metric_exporters["dummy_pull_exporter"],
            DummyMetricReaderPullExporter,
        )


class TestImportConfigComponents(TestCase):
    @patch(
        "opentelemetry.sdk._configuration.entry_points",
        **{"side_effect": KeyError},
    )
    def test__import_config_components_missing_entry_point(
        self, mock_entry_points
    ):
        with raises(RuntimeError) as error:
            _import_config_components(["a", "b", "c"], "name")
        self.assertEqual(
            str(error.value), "Requested entry point 'name' not found"
        )

    @patch(
        "opentelemetry.sdk._configuration.entry_points",
        **{"side_effect": StopIteration},
    )
    def test__import_config_components_missing_component(
        self, mock_entry_points
    ):
        with raises(RuntimeError) as error:
            _import_config_components(["a", "b", "c"], "name")
        self.assertEqual(
            str(error.value),
            "Requested component 'a' not found in entry point 'name'",
        )


class TestConfigurator(TestCase):
    class CustomConfigurator(_OTelSDKConfigurator):
        def _configure(self, **kwargs):
            kwargs["sampler"] = "TEST_SAMPLER"
            super()._configure(**kwargs)

    @patch("opentelemetry.sdk._configuration._initialize_components")
    def test_custom_configurator(self, mock_init_comp):
        custom_configurator = TestConfigurator.CustomConfigurator()
        custom_configurator._configure(
            auto_instrumentation_version="TEST_VERSION2"
        )
        kwargs = {
            "auto_instrumentation_version": "TEST_VERSION2",
            "sampler": "TEST_SAMPLER",
        }
        mock_init_comp.assert_called_once_with(**kwargs)
