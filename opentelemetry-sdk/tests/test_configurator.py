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

import logging
from os import environ
from unittest import TestCase
from unittest.mock import patch

from opentelemetry import trace
from opentelemetry.environment_variables import OTEL_PYTHON_ID_GENERATOR
from opentelemetry.sdk._configuration import (
    _EXPORTER_OTLP,
    _EXPORTER_OTLP_PROTO_GRPC,
    _get_exporter_names,
    _get_id_generator,
    _import_exporters,
    _import_id_generator,
    _init_logging,
    _init_tracing,
)
from opentelemetry.sdk._logs import LoggingHandler
from opentelemetry.sdk._logs.export import ConsoleLogExporter
from opentelemetry.sdk._metrics.export import ConsoleMetricExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.sdk.trace.id_generator import IdGenerator, RandomIdGenerator


class Provider:
    def __init__(self, resource=None, id_generator=None):
        self.id_generator = id_generator
        self.processor = None
        self.resource = resource or Resource.create({})

    def add_span_processor(self, processor):
        self.processor = processor


class DummyLogEmitterProvider:
    def __init__(self, resource=None):
        self.resource = resource
        self.processor = DummyLogProcessor(DummyOTLPLogExporter())

    def add_log_processor(self, processor):
        self.processor = processor

    def get_log_emitter(self, name):
        return DummyLogEmitter(name, self.resource, self.processor)


class DummyLogEmitter:
    def __init__(self, name, resource, processor):
        self.name = name
        self.resource = resource
        self.processor = processor

    def emit(self, record):
        self.processor.emit(record)

    def flush(self):
        pass


class DummyLogProcessor:
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
            "opentelemetry.trace.set_tracer_provider"
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
        _init_tracing({"zipkin": Exporter}, RandomIdGenerator, "test-version")

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
        _init_tracing({"otlp": OTLPSpanExporter}, RandomIdGenerator)

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
    @patch("opentelemetry.sdk._configuration.iter_entry_points")
    def test_trace_init_custom_id_generator(self, mock_iter_entry_points):
        mock_iter_entry_points.configure_mock(
            return_value=[
                IterEntryPoint("custom_id_generator", CustomIdGenerator)
            ]
        )
        id_generator_name = _get_id_generator()
        id_generator = _import_id_generator(id_generator_name)
        _init_tracing({}, id_generator)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsInstance(provider.id_generator, CustomIdGenerator)


class TestLoggingInit(TestCase):
    def setUp(self):
        self.processor_patch = patch(
            "opentelemetry.sdk._configuration.BatchLogProcessor",
            DummyLogProcessor,
        )
        self.provider_patch = patch(
            "opentelemetry.sdk._configuration.LogEmitterProvider",
            DummyLogEmitterProvider,
        )
        self.set_provider_patch = patch(
            "opentelemetry.sdk._configuration.set_log_emitter_provider"
        )

        self.processor_mock = self.processor_patch.start()
        self.provider_mock = self.provider_patch.start()
        self.set_provider_mock = self.set_provider_patch.start()

    def tearDown(self):
        self.processor_patch.stop()
        self.set_provider_patch.stop()
        self.provider_patch.stop()
        root_logger = logging.getLogger("root")
        root_logger.handlers = [
            handler
            for handler in root_logger.handlers
            if not isinstance(handler, LoggingHandler)
        ]

    def test_logging_init_empty(self):
        _init_logging({}, "auto-version")
        self.assertEqual(self.set_provider_mock.call_count, 1)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsInstance(provider, DummyLogEmitterProvider)
        self.assertIsInstance(provider.resource, Resource)
        self.assertEqual(
            provider.resource.attributes.get("telemetry.auto.version"),
            "auto-version",
        )

    @patch.dict(
        environ,
        {"OTEL_RESOURCE_ATTRIBUTES": "service.name=otlp-service"},
    )
    def test_logging_init_exporter(self):
        _init_logging({"otlp": DummyOTLPLogExporter})
        self.assertEqual(self.set_provider_mock.call_count, 1)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsInstance(provider, DummyLogEmitterProvider)
        self.assertIsInstance(provider.resource, Resource)
        self.assertEqual(
            provider.resource.attributes.get("service.name"),
            "otlp-service",
        )
        self.assertIsInstance(provider.processor, DummyLogProcessor)
        self.assertIsInstance(
            provider.processor.exporter, DummyOTLPLogExporter
        )
        logging.getLogger(__name__).error("hello")
        self.assertTrue(provider.processor.exporter.export_called)


class TestExporterNames(TestCase):
    def test_otlp_exporter_overwrite(self):
        for exporter in [_EXPORTER_OTLP, _EXPORTER_OTLP_PROTO_GRPC]:
            self.assertEqual(
                _get_exporter_names(exporter), [_EXPORTER_OTLP_PROTO_GRPC]
            )

    def test_multiple_exporters(self):
        self.assertEqual(
            sorted(_get_exporter_names("jaeger,zipkin")), ["jaeger", "zipkin"]
        )

    def test_none_exporters(self):
        self.assertEqual(sorted(_get_exporter_names("none")), [])

    def test_no_exporters(self):
        self.assertEqual(sorted(_get_exporter_names(None)), [])

    def test_empty_exporters(self):
        self.assertEqual(sorted(_get_exporter_names("")), [])


class TestImportExporters(TestCase):
    def test_console_exporters(self):
        trace_exporters, logs_exporters = _import_exporters(
            ["console"], ["console"]
        )
        self.assertEqual(
            trace_exporters["console"].__class__, ConsoleSpanExporter.__class__
        )
        self.assertEqual(
            logs_exporters["console"].__class__, ConsoleLogExporter.__class__
        )
        self.assertEqual(
            logs_exporters["console"].__class__,
            ConsoleMetricExporter.__class__,
        )
