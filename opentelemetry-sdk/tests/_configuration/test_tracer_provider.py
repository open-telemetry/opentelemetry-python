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

# Tests access private members of SDK classes to assert correct configuration.
# pylint: disable=protected-access

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from opentelemetry.sdk._configuration._tracer_provider import (
    configure_tracer_provider,
    create_tracer_provider,
)
from opentelemetry.sdk._configuration.file._loader import ConfigurationError
from opentelemetry.sdk._configuration.models import (
    BatchSpanProcessor as BatchSpanProcessorConfig,
)
from opentelemetry.sdk._configuration.models import (
    OtlpGrpcExporter as OtlpGrpcExporterConfig,
)
from opentelemetry.sdk._configuration.models import (
    OtlpHttpExporter as OtlpHttpExporterConfig,
)
from opentelemetry.sdk._configuration.models import (
    ParentBasedSampler as ParentBasedSamplerConfig,
)
from opentelemetry.sdk._configuration.models import (
    Sampler as SamplerConfig,
)
from opentelemetry.sdk._configuration.models import (
    SimpleSpanProcessor as SimpleSpanProcessorConfig,
)
from opentelemetry.sdk._configuration.models import (
    SpanLimits as SpanLimitsConfig,
)
from opentelemetry.sdk._configuration.models import (
    SpanProcessor as SpanProcessorConfig,
)
from opentelemetry.sdk._configuration.models import (
    TraceIdRatioBasedSampler as TraceIdRatioBasedConfig,
)
from opentelemetry.sdk._configuration.models import (
    TracerProvider as TracerProviderConfig,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.sdk.trace.sampling import (
    ALWAYS_OFF,
    ALWAYS_ON,
    ParentBased,
    TraceIdRatioBased,
)


class TestCreateTracerProviderBasic(unittest.TestCase):
    def test_none_config_returns_provider(self):
        resource = Resource({"service.name": "test"})
        provider = create_tracer_provider(None, resource)
        self.assertIsInstance(provider, TracerProvider)

    def test_none_config_uses_supplied_resource(self):
        resource = Resource({"service.name": "svc"})
        provider = create_tracer_provider(None, resource)
        self.assertIs(provider._resource, resource)

    def test_none_config_uses_default_sampler(self):
        provider = create_tracer_provider(None)
        self.assertIsInstance(provider.sampler, ParentBased)

    def test_none_config_no_processors(self):
        provider = create_tracer_provider(None)
        self.assertEqual(
            len(provider._active_span_processor._span_processors), 0
        )

    def test_none_config_does_not_read_sampler_env_var(self):
        with patch.dict(os.environ, {"OTEL_TRACES_SAMPLER": "always_off"}):
            provider = create_tracer_provider(None)
        self.assertIsInstance(provider.sampler, ParentBased)

    def test_none_config_does_not_read_span_limit_env_var(self):
        with patch.dict(os.environ, {"OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT": "1"}):
            provider = create_tracer_provider(None)
        self.assertEqual(provider._span_limits.max_span_attributes, 128)

    def test_configure_none_does_not_set_global(self):
        original = __import__(
            "opentelemetry.trace", fromlist=["get_tracer_provider"]
        ).get_tracer_provider()
        configure_tracer_provider(None)
        after = __import__(
            "opentelemetry.trace", fromlist=["get_tracer_provider"]
        ).get_tracer_provider()
        self.assertIs(original, after)

    def test_configure_with_config_sets_global(self):
        config = TracerProviderConfig(processors=[])
        with patch(
            "opentelemetry.sdk._configuration._tracer_provider.trace.set_tracer_provider"
        ) as mock_set:
            configure_tracer_provider(config)
            mock_set.assert_called_once()
            arg = mock_set.call_args[0][0]
            self.assertIsInstance(arg, TracerProvider)

    def test_processors_added_in_order(self):
        mock_proc_a = MagicMock()
        mock_proc_b = MagicMock()
        config = TracerProviderConfig(processors=[])
        provider = create_tracer_provider(config)
        provider.add_span_processor(mock_proc_a)
        provider.add_span_processor(mock_proc_b)
        procs = provider._active_span_processor._span_processors
        self.assertIs(procs[0], mock_proc_a)
        self.assertIs(procs[1], mock_proc_b)

    def test_span_limits_from_config(self):
        config = TracerProviderConfig(
            processors=[],
            limits=SpanLimitsConfig(
                attribute_count_limit=5,
                event_count_limit=10,
                link_count_limit=3,
            ),
        )
        provider = create_tracer_provider(config)
        self.assertEqual(provider._span_limits.max_span_attributes, 5)
        self.assertEqual(provider._span_limits.max_events, 10)
        self.assertEqual(provider._span_limits.max_links, 3)


class TestCreateSampler(unittest.TestCase):
    @staticmethod
    def _make_provider(sampler_config):
        return create_tracer_provider(
            TracerProviderConfig(processors=[], sampler=sampler_config)
        )

    def test_always_on(self):
        provider = self._make_provider(SamplerConfig(always_on={}))
        self.assertIs(provider.sampler, ALWAYS_ON)

    def test_always_off(self):
        provider = self._make_provider(SamplerConfig(always_off={}))
        self.assertIs(provider.sampler, ALWAYS_OFF)

    def test_trace_id_ratio_based(self):
        provider = self._make_provider(
            SamplerConfig(
                trace_id_ratio_based=TraceIdRatioBasedConfig(ratio=0.5)
            )
        )
        self.assertIsInstance(provider.sampler, TraceIdRatioBased)
        self.assertAlmostEqual(provider.sampler._rate, 0.5)

    def test_trace_id_ratio_based_none_ratio_defaults_to_1(self):
        provider = self._make_provider(
            SamplerConfig(trace_id_ratio_based=TraceIdRatioBasedConfig())
        )
        self.assertIsInstance(provider.sampler, TraceIdRatioBased)
        self.assertAlmostEqual(provider.sampler._rate, 1.0)

    def test_parent_based_with_root(self):
        provider = self._make_provider(
            SamplerConfig(
                parent_based=ParentBasedSamplerConfig(
                    root=SamplerConfig(always_on={})
                )
            )
        )
        self.assertIsInstance(provider.sampler, ParentBased)

    def test_parent_based_no_root_defaults_to_always_on(self):
        provider = self._make_provider(
            SamplerConfig(parent_based=ParentBasedSamplerConfig())
        )
        self.assertIsInstance(provider.sampler, ParentBased)
        self.assertIs(provider.sampler._root, ALWAYS_ON)

    def test_parent_based_with_delegate_samplers(self):
        provider = self._make_provider(
            SamplerConfig(
                parent_based=ParentBasedSamplerConfig(
                    root=SamplerConfig(always_on={}),
                    remote_parent_sampled=SamplerConfig(always_on={}),
                    remote_parent_not_sampled=SamplerConfig(always_off={}),
                    local_parent_sampled=SamplerConfig(always_on={}),
                    local_parent_not_sampled=SamplerConfig(always_off={}),
                )
            )
        )
        sampler = provider.sampler
        self.assertIsInstance(sampler, ParentBased)
        self.assertIs(sampler._remote_parent_sampled, ALWAYS_ON)
        self.assertIs(sampler._remote_parent_not_sampled, ALWAYS_OFF)
        self.assertIs(sampler._local_parent_sampled, ALWAYS_ON)
        self.assertIs(sampler._local_parent_not_sampled, ALWAYS_OFF)

    def test_unknown_sampler_raises_configuration_error(self):
        with self.assertRaises(ConfigurationError):
            create_tracer_provider(
                TracerProviderConfig(processors=[], sampler=SamplerConfig())
            )


class TestCreateSpanExporterAndProcessor(unittest.TestCase):
    # pylint: disable=no-self-use

    @staticmethod
    def _make_batch_config(exporter_config):
        return TracerProviderConfig(
            processors=[
                SpanProcessorConfig(
                    batch=BatchSpanProcessorConfig(exporter=exporter_config)
                )
            ]
        )

    @staticmethod
    def _make_simple_config(exporter_config):
        return TracerProviderConfig(
            processors=[
                SpanProcessorConfig(
                    simple=SimpleSpanProcessorConfig(exporter=exporter_config)
                )
            ]
        )

    def test_console_exporter_batch(self):
        config = self._make_batch_config({"console": {}})
        provider = create_tracer_provider(config)
        procs = provider._active_span_processor._span_processors
        self.assertEqual(len(procs), 1)
        self.assertIsInstance(procs[0], BatchSpanProcessor)
        self.assertIsInstance(procs[0].span_exporter, ConsoleSpanExporter)

    def test_console_exporter_simple(self):
        config = self._make_simple_config({"console": {}})
        provider = create_tracer_provider(config)
        procs = provider._active_span_processor._span_processors
        self.assertIsInstance(procs[0], SimpleSpanProcessor)
        self.assertIsInstance(procs[0].span_exporter, ConsoleSpanExporter)

    def test_otlp_http_missing_package_raises(self):
        config = self._make_batch_config(
            {"otlp_http": OtlpHttpExporterConfig()}
        )
        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.proto.http.trace_exporter": None,
                "opentelemetry.exporter.otlp.proto.http": None,
            },
        ):
            with self.assertRaises(ConfigurationError) as ctx:
                create_tracer_provider(config)
        self.assertIn("otlp-proto-http", str(ctx.exception))

    def test_otlp_http_created_with_endpoint(self):
        mock_exporter_cls = MagicMock()
        mock_compression_cls = MagicMock()
        mock_compression_cls.Gzip = "gzip_val"
        mock_module = MagicMock()
        mock_module.OTLPSpanExporter = mock_exporter_cls
        mock_http_module = MagicMock()
        mock_http_module.Compression = mock_compression_cls

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.proto.http.trace_exporter": mock_module,
                "opentelemetry.exporter.otlp.proto.http": mock_http_module,
            },
        ):
            config = self._make_batch_config(
                {
                    "otlp_http": OtlpHttpExporterConfig(
                        endpoint="http://localhost:4318"
                    )
                }
            )
            create_tracer_provider(config)

        mock_exporter_cls.assert_called_once_with(
            endpoint="http://localhost:4318",
            headers=None,
            timeout=None,
            compression=None,
        )

    def test_otlp_http_headers_list(self):
        mock_exporter_cls = MagicMock()
        mock_http_module = MagicMock()
        mock_module = MagicMock()
        mock_module.OTLPSpanExporter = mock_exporter_cls

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.proto.http.trace_exporter": mock_module,
                "opentelemetry.exporter.otlp.proto.http": mock_http_module,
            },
        ):
            config = self._make_batch_config(
                {
                    "otlp_http": OtlpHttpExporterConfig(
                        headers_list="x-api-key=secret,env=prod"
                    )
                }
            )
            create_tracer_provider(config)

        _, kwargs = mock_exporter_cls.call_args
        self.assertEqual(
            kwargs["headers"], {"x-api-key": "secret", "env": "prod"}
        )

    def test_otlp_grpc_missing_package_raises(self):
        config = self._make_batch_config(
            {"otlp_grpc": OtlpGrpcExporterConfig()}
        )
        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": None,
                "grpc": None,
            },
        ):
            with self.assertRaises(ConfigurationError) as ctx:
                create_tracer_provider(config)
        self.assertIn("otlp-proto-grpc", str(ctx.exception))

    def test_no_processor_type_raises(self):
        config = TracerProviderConfig(processors=[SpanProcessorConfig()])
        with self.assertRaises(ConfigurationError):
            create_tracer_provider(config)

    def test_no_exporter_type_raises(self):
        config = self._make_batch_config({})
        with self.assertRaises(ConfigurationError):
            create_tracer_provider(config)

    def test_plugin_span_exporter_loaded_via_entry_point(self):
        mock_exporter = MagicMock()
        mock_class = MagicMock(return_value=mock_exporter)
        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[MagicMock(**{"load.return_value": mock_class})],
        ):
            config = self._make_batch_config({"my_custom_exporter": {}})
            provider = create_tracer_provider(config)
        self.assertEqual(
            len(provider._active_span_processor._span_processors), 1
        )

    def test_unknown_span_exporter_raises_configuration_error(self):
        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[],
        ):
            config = self._make_batch_config({"no_such_exporter": {}})
            with self.assertRaises(ConfigurationError):
                create_tracer_provider(config)


class TestCreateSpanLimits(unittest.TestCase):
    # pylint: disable=no-self-use

    @staticmethod
    def _create_with_limits(limits_config):
        return create_tracer_provider(
            TracerProviderConfig(processors=[], limits=limits_config)
        )

    def test_explicit_attribute_count_limit(self):
        provider = self._create_with_limits(
            SpanLimitsConfig(attribute_count_limit=10)
        )
        self.assertEqual(provider._span_limits.max_span_attributes, 10)

    def test_explicit_event_count_limit(self):
        provider = self._create_with_limits(
            SpanLimitsConfig(event_count_limit=5)
        )
        self.assertEqual(provider._span_limits.max_events, 5)

    def test_explicit_link_count_limit(self):
        provider = self._create_with_limits(
            SpanLimitsConfig(link_count_limit=2)
        )
        self.assertEqual(provider._span_limits.max_links, 2)

    def test_explicit_attribute_value_length_limit(self):
        provider = self._create_with_limits(
            SpanLimitsConfig(attribute_value_length_limit=64)
        )
        self.assertEqual(provider._span_limits.max_attribute_length, 64)

    def test_absent_limits_use_spec_defaults(self):
        provider = self._create_with_limits(SpanLimitsConfig())
        self.assertEqual(provider._span_limits.max_span_attributes, 128)
        self.assertEqual(provider._span_limits.max_events, 128)
        self.assertEqual(provider._span_limits.max_links, 128)

    def test_absent_limits_do_not_read_env_vars(self):
        with patch.dict(
            os.environ,
            {
                "OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT": "1",
                "OTEL_SPAN_EVENT_COUNT_LIMIT": "2",
            },
        ):
            provider = self._create_with_limits(SpanLimitsConfig())
        self.assertEqual(provider._span_limits.max_span_attributes, 128)
        self.assertEqual(provider._span_limits.max_events, 128)
