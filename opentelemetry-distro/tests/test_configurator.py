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

from os import environ
from unittest import TestCase
from unittest.mock import patch

from opentelemetry import trace
from opentelemetry.distro import (
    EXPORTER_OTLP,
    EXPORTER_OTLP_METRIC,
    EXPORTER_OTLP_SPAN,
    _get_exporter_names,
    _get_id_generator,
    _import_id_generator,
    _init_tracing,
)
from opentelemetry.environment_variables import (
    OTEL_METRICS_EXPORTER,
    OTEL_PYTHON_ID_GENERATOR,
    OTEL_TRACES_EXPORTER,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace.id_generator import IdGenerator, RandomIdGenerator


class Provider:
    def __init__(self, resource=None, id_generator=None):
        self.id_generator = id_generator
        self.processor = None
        self.resource = resource or Resource.create({})

    def add_span_processor(self, processor):
        self.processor = processor


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


class OTLPExporter:
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
            "opentelemetry.distro.TracerProvider", Provider
        )
        self.get_processor_patcher = patch(
            "opentelemetry.distro.BatchSpanProcessor", Processor
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
        _init_tracing({"zipkin": Exporter}, RandomIdGenerator)

        self.assertEqual(self.set_provider_mock.call_count, 1)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsInstance(provider, Provider)
        self.assertIsInstance(provider.id_generator, RandomIdGenerator)
        self.assertIsInstance(provider.processor, Processor)
        self.assertIsInstance(provider.processor.exporter, Exporter)
        self.assertEqual(
            provider.processor.exporter.service_name, "my-test-service"
        )

    @patch.dict(
        environ,
        {"OTEL_RESOURCE_ATTRIBUTES": "service.name=my-otlp-test-service"},
    )
    def test_trace_init_otlp(self):
        _init_tracing({"otlp": OTLPExporter}, RandomIdGenerator)

        self.assertEqual(self.set_provider_mock.call_count, 1)
        provider = self.set_provider_mock.call_args[0][0]
        self.assertIsInstance(provider, Provider)
        self.assertIsInstance(provider.id_generator, RandomIdGenerator)
        self.assertIsInstance(provider.processor, Processor)
        self.assertIsInstance(provider.processor.exporter, OTLPExporter)
        self.assertIsInstance(provider.resource, Resource)
        self.assertEqual(
            provider.resource.attributes.get("service.name"),
            "my-otlp-test-service",
        )

    @patch.dict(environ, {OTEL_PYTHON_ID_GENERATOR: "custom_id_generator"})
    @patch("opentelemetry.distro.IdGenerator", new=IdGenerator)
    @patch("opentelemetry.distro.iter_entry_points")
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


class TestTracesExporterNames(TestCase):
    def test_otlp_exporter_overwrite(self):
        for exporter in [EXPORTER_OTLP, EXPORTER_OTLP_SPAN]:
            with patch.dict(environ, {OTEL_TRACES_EXPORTER: exporter}):
                self.assertEqual(_get_exporter_names(), [EXPORTER_OTLP_SPAN])

    @patch.dict(environ, {OTEL_TRACES_EXPORTER: "jaeger,zipkin"})
    def test_multiple_exporters(self):
        self.assertEqual(sorted(_get_exporter_names()), ["jaeger", "zipkin"])

    @patch.dict(environ, {OTEL_TRACES_EXPORTER: "none"})
    def test_none_exporters(self):
        self.assertEqual(sorted(_get_exporter_names()), [])

    @patch.dict(environ, {}, clear=True)
    def test_no_exporters(self):
        self.assertEqual(sorted(_get_exporter_names()), [])

    @patch.dict(environ, {OTEL_TRACES_EXPORTER: ""})
    def test_empty_exporters(self):
        self.assertEqual(sorted(_get_exporter_names()), [])


class TestMetricsExporterNames(TestCase):
    def test_otlp_exporter_overwrite(self):
        for exporter in [EXPORTER_OTLP, EXPORTER_OTLP_METRIC]:
            with patch.dict(environ, {OTEL_METRICS_EXPORTER: exporter}):
                self.assertEqual(_get_exporter_names(), [EXPORTER_OTLP_METRIC])

    @patch.dict(
        environ, {OTEL_METRICS_EXPORTER: "otlp_proto_grpc_metric,prometheus"}
    )
    def test_multiple_exporters(self):
        self.assertEqual(
            sorted(_get_exporter_names()),
            ["otlp_proto_grpc_metric", "prometheus"],
        )

    @patch.dict(environ, {OTEL_METRICS_EXPORTER: "none"})
    def test_none_exporters(self):
        self.assertEqual(sorted(_get_exporter_names()), [])

    @patch.dict(environ, {}, clear=True)
    def test_no_exporters(self):
        self.assertEqual(sorted(_get_exporter_names()), [])

    @patch.dict(environ, {OTEL_METRICS_EXPORTER: ""})
    def test_empty_exporters(self):
        self.assertEqual(sorted(_get_exporter_names()), [])
