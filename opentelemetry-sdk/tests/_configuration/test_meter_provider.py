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

from opentelemetry.sdk._configuration._meter_provider import (
    configure_meter_provider,
    create_meter_provider,
)
from opentelemetry.sdk._configuration.file._loader import ConfigurationError
from opentelemetry.sdk._configuration.models import (
    Aggregation as AggregationConfig,
)
from opentelemetry.sdk._configuration.models import (
    Base2ExponentialBucketHistogramAggregation as Base2Config,
)
from opentelemetry.sdk._configuration.models import (
    ConsoleMetricExporter as ConsoleMetricExporterConfig,
)
from opentelemetry.sdk._configuration.models import (
    ExemplarFilter as ExemplarFilterConfig,
)
from opentelemetry.sdk._configuration.models import (
    ExplicitBucketHistogramAggregation as ExplicitBucketConfig,
)
from opentelemetry.sdk._configuration.models import (
    ExporterDefaultHistogramAggregation,
    ExporterTemporalityPreference,
    IncludeExclude,
    InstrumentType,
    ViewSelector,
    ViewStream,
)
from opentelemetry.sdk._configuration.models import (
    MeterProvider as MeterProviderConfig,
)
from opentelemetry.sdk._configuration.models import (
    MetricReader as MetricReaderConfig,
)
from opentelemetry.sdk._configuration.models import (
    OtlpGrpcMetricExporter as OtlpGrpcMetricExporterConfig,
)
from opentelemetry.sdk._configuration.models import (
    OtlpHttpMetricExporter as OtlpHttpMetricExporterConfig,
)
from opentelemetry.sdk._configuration.models import (
    PeriodicMetricReader as PeriodicMetricReaderConfig,
)
from opentelemetry.sdk._configuration.models import (
    PushMetricExporter as PushMetricExporterConfig,
)
from opentelemetry.sdk._configuration.models import (
    View as ViewConfig,
)
from opentelemetry.sdk.metrics import (
    AlwaysOffExemplarFilter,
    AlwaysOnExemplarFilter,
    Counter,
    Histogram,
    MeterProvider,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    TraceBasedExemplarFilter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.metrics.view import (
    DefaultAggregation,
    DropAggregation,
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
    LastValueAggregation,
    SumAggregation,
    View,
)
from opentelemetry.sdk.resources import Resource


class TestCreateMeterProviderBasic(unittest.TestCase):
    def test_none_config_returns_provider(self):
        provider = create_meter_provider(None)
        self.assertIsInstance(provider, MeterProvider)

    def test_none_config_uses_supplied_resource(self):
        resource = Resource({"service.name": "svc"})
        provider = create_meter_provider(None, resource)
        self.assertIs(provider._sdk_config.resource, resource)

    def test_none_config_no_readers(self):
        provider = create_meter_provider(None)
        self.assertEqual(len(provider._sdk_config.metric_readers), 0)

    def test_none_config_uses_trace_based_exemplar_filter(self):
        provider = create_meter_provider(None)
        self.assertIsInstance(
            provider._sdk_config.exemplar_filter, TraceBasedExemplarFilter
        )

    def test_none_config_does_not_read_exemplar_filter_env_var(self):
        with patch.dict(
            os.environ, {"OTEL_METRICS_EXEMPLAR_FILTER": "always_on"}
        ):
            provider = create_meter_provider(None)
        self.assertIsInstance(
            provider._sdk_config.exemplar_filter, TraceBasedExemplarFilter
        )

    def test_none_config_does_not_read_interval_env_var(self):
        config = MeterProviderConfig(
            readers=[
                MetricReaderConfig(
                    periodic=PeriodicMetricReaderConfig(
                        exporter=PushMetricExporterConfig(
                            console=ConsoleMetricExporterConfig()
                        )
                    )
                )
            ]
        )
        with patch.dict(os.environ, {"OTEL_METRIC_EXPORT_INTERVAL": "999999"}):
            provider = create_meter_provider(config)
        reader = provider._sdk_config.metric_readers[0]
        self.assertIsInstance(reader, PeriodicExportingMetricReader)
        self.assertEqual(reader._export_interval_millis, 60000.0)

    def test_configure_none_does_not_set_global(self):
        original = __import__(
            "opentelemetry.metrics", fromlist=["get_meter_provider"]
        ).get_meter_provider()
        configure_meter_provider(None)
        after = __import__(
            "opentelemetry.metrics", fromlist=["get_meter_provider"]
        ).get_meter_provider()
        self.assertIs(original, after)

    def test_configure_with_config_sets_global(self):
        config = MeterProviderConfig(readers=[])
        with patch(
            "opentelemetry.sdk._configuration._meter_provider.metrics.set_meter_provider"
        ) as mock_set:
            configure_meter_provider(config)
            mock_set.assert_called_once()
            arg = mock_set.call_args[0][0]
            self.assertIsInstance(arg, MeterProvider)

    def test_empty_readers_list(self):
        config = MeterProviderConfig(readers=[])
        provider = create_meter_provider(config)
        self.assertEqual(len(provider._sdk_config.metric_readers), 0)


class TestCreateMetricReaders(unittest.TestCase):
    @staticmethod
    def _make_periodic_config(exporter_config, interval=None, timeout=None):
        return MeterProviderConfig(
            readers=[
                MetricReaderConfig(
                    periodic=PeriodicMetricReaderConfig(
                        exporter=exporter_config,
                        interval=interval,
                        timeout=timeout,
                    )
                )
            ]
        )

    def test_console_exporter(self):
        config = self._make_periodic_config(
            PushMetricExporterConfig(console=ConsoleMetricExporterConfig())
        )
        provider = create_meter_provider(config)
        reader = provider._sdk_config.metric_readers[0]
        self.assertIsInstance(reader, PeriodicExportingMetricReader)
        self.assertIsInstance(reader._exporter, ConsoleMetricExporter)

    def test_periodic_reader_default_interval(self):
        config = self._make_periodic_config(
            PushMetricExporterConfig(console=ConsoleMetricExporterConfig())
        )
        provider = create_meter_provider(config)
        reader = provider._sdk_config.metric_readers[0]
        self.assertEqual(reader._export_interval_millis, 60000.0)

    def test_periodic_reader_default_timeout(self):
        config = self._make_periodic_config(
            PushMetricExporterConfig(console=ConsoleMetricExporterConfig())
        )
        provider = create_meter_provider(config)
        reader = provider._sdk_config.metric_readers[0]
        self.assertEqual(reader._export_timeout_millis, 30000.0)

    def test_periodic_reader_explicit_interval(self):
        config = self._make_periodic_config(
            PushMetricExporterConfig(console=ConsoleMetricExporterConfig()),
            interval=5000,
        )
        provider = create_meter_provider(config)
        reader = provider._sdk_config.metric_readers[0]
        self.assertEqual(reader._export_interval_millis, 5000.0)

    def test_periodic_reader_explicit_timeout(self):
        config = self._make_periodic_config(
            PushMetricExporterConfig(console=ConsoleMetricExporterConfig()),
            timeout=10000,
        )
        provider = create_meter_provider(config)
        reader = provider._sdk_config.metric_readers[0]
        self.assertEqual(reader._export_timeout_millis, 10000.0)

    def test_otlp_http_missing_package_raises(self):
        config = self._make_periodic_config(
            PushMetricExporterConfig(otlp_http=OtlpHttpMetricExporterConfig())
        )
        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.proto.http.metric_exporter": None,
                "opentelemetry.exporter.otlp.proto.http": None,
            },
        ):
            with self.assertRaises(ConfigurationError) as ctx:
                create_meter_provider(config)
        self.assertIn("otlp-proto-http", str(ctx.exception))

    def test_otlp_http_created_with_endpoint(self):
        mock_exporter_cls = MagicMock()
        mock_compression_cls = MagicMock()
        mock_http_module = MagicMock()
        mock_http_module.Compression = mock_compression_cls
        mock_module = MagicMock()
        mock_module.OTLPMetricExporter = mock_exporter_cls

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.proto.http.metric_exporter": mock_module,
                "opentelemetry.exporter.otlp.proto.http": mock_http_module,
            },
        ):
            config = self._make_periodic_config(
                PushMetricExporterConfig(
                    otlp_http=OtlpHttpMetricExporterConfig(
                        endpoint="http://localhost:4318"
                    )
                )
            )
            create_meter_provider(config)

        _, kwargs = mock_exporter_cls.call_args
        self.assertEqual(kwargs["endpoint"], "http://localhost:4318")
        self.assertIsNone(kwargs["headers"])
        self.assertIsNone(kwargs["timeout"])
        self.assertIsNone(kwargs["compression"])

    def test_otlp_http_created_with_deflate_compression(self):
        mock_exporter_cls = MagicMock()
        mock_compression_cls = MagicMock()
        mock_compression_cls.Deflate = "deflate_val"
        mock_http_module = MagicMock()
        mock_http_module.Compression = mock_compression_cls
        mock_module = MagicMock()
        mock_module.OTLPMetricExporter = mock_exporter_cls

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.proto.http.metric_exporter": mock_module,
                "opentelemetry.exporter.otlp.proto.http": mock_http_module,
            },
        ):
            config = self._make_periodic_config(
                PushMetricExporterConfig(
                    otlp_http=OtlpHttpMetricExporterConfig(
                        compression="deflate"
                    )
                )
            )
            create_meter_provider(config)

        _, kwargs = mock_exporter_cls.call_args
        self.assertEqual(kwargs["compression"], "deflate_val")

    def test_otlp_grpc_missing_package_raises(self):
        config = self._make_periodic_config(
            PushMetricExporterConfig(otlp_grpc=OtlpGrpcMetricExporterConfig())
        )
        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.proto.grpc.metric_exporter": None,
                "grpc": None,
            },
        ):
            with self.assertRaises(ConfigurationError) as ctx:
                create_meter_provider(config)
        self.assertIn("otlp-proto-grpc", str(ctx.exception))

    def test_pull_reader_raises(self):
        config = MeterProviderConfig(
            readers=[MetricReaderConfig(pull=MagicMock())]
        )
        with self.assertRaises(ConfigurationError):
            create_meter_provider(config)

    def test_no_reader_type_raises(self):
        config = MeterProviderConfig(readers=[MetricReaderConfig()])
        with self.assertRaises(ConfigurationError):
            create_meter_provider(config)

    def test_no_exporter_type_raises(self):
        config = self._make_periodic_config(PushMetricExporterConfig())
        with self.assertRaises(ConfigurationError):
            create_meter_provider(config)

    def test_multiple_readers(self):
        config = MeterProviderConfig(
            readers=[
                MetricReaderConfig(
                    periodic=PeriodicMetricReaderConfig(
                        exporter=PushMetricExporterConfig(
                            console=ConsoleMetricExporterConfig()
                        )
                    )
                ),
                MetricReaderConfig(
                    periodic=PeriodicMetricReaderConfig(
                        exporter=PushMetricExporterConfig(
                            console=ConsoleMetricExporterConfig()
                        )
                    )
                ),
            ]
        )
        provider = create_meter_provider(config)
        self.assertEqual(len(provider._sdk_config.metric_readers), 2)


class TestTemporalityAndAggregation(unittest.TestCase):
    @staticmethod
    def _make_console_config(temporality=None, histogram_agg=None):
        return MeterProviderConfig(
            readers=[
                MetricReaderConfig(
                    periodic=PeriodicMetricReaderConfig(
                        exporter=PushMetricExporterConfig(
                            console=ConsoleMetricExporterConfig(
                                temporality_preference=temporality,
                                default_histogram_aggregation=histogram_agg,
                            )
                        )
                    )
                )
            ]
        )

    @staticmethod
    def _get_exporter(config):
        provider = create_meter_provider(config)
        return provider._sdk_config.metric_readers[0]._exporter

    def test_default_temporality_is_cumulative(self):
        exporter = self._get_exporter(self._make_console_config())
        for instrument_type in (
            Counter,
            UpDownCounter,
            Histogram,
            ObservableCounter,
            ObservableGauge,
            ObservableUpDownCounter,
        ):
            self.assertEqual(
                exporter._preferred_temporality[instrument_type],
                AggregationTemporality.CUMULATIVE,
            )

    def test_cumulative_temporality(self):
        exporter = self._get_exporter(
            self._make_console_config(
                temporality=ExporterTemporalityPreference.cumulative
            )
        )
        self.assertEqual(
            exporter._preferred_temporality[Counter],
            AggregationTemporality.CUMULATIVE,
        )

    def test_delta_temporality(self):
        exporter = self._get_exporter(
            self._make_console_config(
                temporality=ExporterTemporalityPreference.delta
            )
        )
        self.assertEqual(
            exporter._preferred_temporality[Counter],
            AggregationTemporality.DELTA,
        )
        self.assertEqual(
            exporter._preferred_temporality[Histogram],
            AggregationTemporality.DELTA,
        )
        self.assertEqual(
            exporter._preferred_temporality[UpDownCounter],
            AggregationTemporality.CUMULATIVE,
        )
        self.assertEqual(
            exporter._preferred_temporality[ObservableCounter],
            AggregationTemporality.DELTA,
        )

    def test_low_memory_temporality(self):
        exporter = self._get_exporter(
            self._make_console_config(
                temporality=ExporterTemporalityPreference.low_memory
            )
        )
        self.assertEqual(
            exporter._preferred_temporality[Counter],
            AggregationTemporality.DELTA,
        )
        self.assertEqual(
            exporter._preferred_temporality[ObservableCounter],
            AggregationTemporality.CUMULATIVE,
        )

    def test_default_histogram_aggregation_is_explicit(self):
        exporter = self._get_exporter(self._make_console_config())
        self.assertIsInstance(
            exporter._preferred_aggregation[Histogram],
            ExplicitBucketHistogramAggregation,
        )

    def test_explicit_histogram_aggregation(self):
        exporter = self._get_exporter(
            self._make_console_config(
                histogram_agg=ExporterDefaultHistogramAggregation.explicit_bucket_histogram
            )
        )
        self.assertIsInstance(
            exporter._preferred_aggregation[Histogram],
            ExplicitBucketHistogramAggregation,
        )

    def test_base2_exponential_histogram_aggregation(self):
        exporter = self._get_exporter(
            self._make_console_config(
                histogram_agg=ExporterDefaultHistogramAggregation.base2_exponential_bucket_histogram
            )
        )
        self.assertIsInstance(
            exporter._preferred_aggregation[Histogram],
            ExponentialBucketHistogramAggregation,
        )

    def test_temporality_suppresses_env_var(self):
        with patch.dict(
            os.environ,
            {"OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE": "DELTA"},
        ):
            exporter = self._get_exporter(self._make_console_config())
        # Config has no preference → default cumulative, env var ignored
        self.assertEqual(
            exporter._preferred_temporality[Counter],
            AggregationTemporality.CUMULATIVE,
        )


class TestCreateViews(unittest.TestCase):
    @staticmethod
    def _make_view_config(selector_kwargs=None, stream_kwargs=None):
        selector = ViewSelector(
            **(selector_kwargs or {"instrument_name": "*"})
        )
        stream = ViewStream(**(stream_kwargs or {}))
        return MeterProviderConfig(
            readers=[],
            views=[ViewConfig(selector=selector, stream=stream)],
        )

    @staticmethod
    def _get_view(config):
        provider = create_meter_provider(config)
        return provider._sdk_config.views[0]

    def test_view_created(self):
        config = self._make_view_config()
        provider = create_meter_provider(config)
        self.assertEqual(len(provider._sdk_config.views), 1)
        self.assertIsInstance(provider._sdk_config.views[0], View)

    def test_selector_instrument_name(self):
        view = self._get_view(
            self._make_view_config({"instrument_name": "my.metric"})
        )
        self.assertEqual(view._instrument_name, "my.metric")

    def test_selector_instrument_type(self):
        view = self._get_view(
            self._make_view_config({"instrument_type": InstrumentType.counter})
        )
        self.assertIs(view._instrument_type, Counter)

    def test_selector_meter_name(self):
        view = self._get_view(
            self._make_view_config({"meter_name": "my.meter"})
        )
        self.assertEqual(view._meter_name, "my.meter")

    def test_stream_name(self):
        view = self._get_view(
            self._make_view_config(
                {"instrument_name": "my.metric"},
                stream_kwargs={"name": "renamed"},
            )
        )
        self.assertEqual(view._name, "renamed")

    def test_stream_description(self):
        view = self._get_view(
            self._make_view_config(
                stream_kwargs={"description": "a description"}
            )
        )
        self.assertEqual(view._description, "a description")

    def test_stream_attribute_keys_included(self):
        view = self._get_view(
            self._make_view_config(
                stream_kwargs={
                    "attribute_keys": IncludeExclude(included=["key1", "key2"])
                }
            )
        )
        self.assertEqual(view._attribute_keys, {"key1", "key2"})

    def test_stream_attribute_keys_excluded_logs_warning(self):
        config = self._make_view_config(
            stream_kwargs={"attribute_keys": IncludeExclude(excluded=["key1"])}
        )
        with self.assertLogs(
            "opentelemetry.sdk._configuration._meter_provider", level="WARNING"
        ) as log:
            create_meter_provider(config)
        self.assertTrue(any("excluded" in msg for msg in log.output))

    def test_stream_aggregation_drop(self):
        view = self._get_view(
            self._make_view_config(
                stream_kwargs={"aggregation": AggregationConfig(drop={})}
            )
        )
        self.assertIsInstance(view._aggregation, DropAggregation)

    def test_stream_aggregation_explicit_bucket_histogram_with_boundaries(
        self,
    ):
        view = self._get_view(
            self._make_view_config(
                stream_kwargs={
                    "aggregation": AggregationConfig(
                        explicit_bucket_histogram=ExplicitBucketConfig(
                            boundaries=[1.0, 5.0, 10.0]
                        )
                    )
                }
            )
        )
        self.assertIsInstance(
            view._aggregation, ExplicitBucketHistogramAggregation
        )
        self.assertEqual(list(view._aggregation._boundaries), [1.0, 5.0, 10.0])

    def test_stream_aggregation_base2_exponential_with_params(self):
        view = self._get_view(
            self._make_view_config(
                stream_kwargs={
                    "aggregation": AggregationConfig(
                        base2_exponential_bucket_histogram=Base2Config(
                            max_size=64, max_scale=5
                        )
                    )
                }
            )
        )
        self.assertIsInstance(
            view._aggregation, ExponentialBucketHistogramAggregation
        )

    def test_stream_aggregation_last_value(self):
        view = self._get_view(
            self._make_view_config(
                stream_kwargs={"aggregation": AggregationConfig(last_value={})}
            )
        )
        self.assertIsInstance(view._aggregation, LastValueAggregation)

    def test_stream_aggregation_sum(self):
        view = self._get_view(
            self._make_view_config(
                stream_kwargs={"aggregation": AggregationConfig(sum={})}
            )
        )
        self.assertIsInstance(view._aggregation, SumAggregation)

    def test_stream_aggregation_default(self):
        view = self._get_view(
            self._make_view_config(
                stream_kwargs={"aggregation": AggregationConfig(default={})}
            )
        )
        self.assertIsInstance(view._aggregation, DefaultAggregation)


class TestExemplarFilter(unittest.TestCase):
    @staticmethod
    def _make_config(exemplar_filter):
        return MeterProviderConfig(readers=[], exemplar_filter=exemplar_filter)

    def test_always_on(self):
        provider = create_meter_provider(
            self._make_config(ExemplarFilterConfig.always_on)
        )
        self.assertIsInstance(
            provider._sdk_config.exemplar_filter, AlwaysOnExemplarFilter
        )

    def test_always_off(self):
        provider = create_meter_provider(
            self._make_config(ExemplarFilterConfig.always_off)
        )
        self.assertIsInstance(
            provider._sdk_config.exemplar_filter, AlwaysOffExemplarFilter
        )

    def test_trace_based(self):
        provider = create_meter_provider(
            self._make_config(ExemplarFilterConfig.trace_based)
        )
        self.assertIsInstance(
            provider._sdk_config.exemplar_filter, TraceBasedExemplarFilter
        )

    def test_absent_defaults_to_trace_based(self):
        provider = create_meter_provider(MeterProviderConfig(readers=[]))
        self.assertIsInstance(
            provider._sdk_config.exemplar_filter, TraceBasedExemplarFilter
        )
