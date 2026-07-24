# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Tests access private members of SDK classes to assert correct configuration.
# pylint: disable=protected-access

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from opentelemetry.configuration._conversion import _dict_to_dataclass
from opentelemetry.configuration._meter_provider import (
    configure_meter_provider,
    create_meter_provider,
)
from opentelemetry.configuration.file._loader import ConfigurationError
from opentelemetry.configuration.models import (
    Aggregation as AggregationConfig,
)
from opentelemetry.configuration.models import (
    Base2ExponentialBucketHistogramAggregation as Base2Config,
)
from opentelemetry.configuration.models import (
    ConsoleMetricExporter as ConsoleMetricExporterConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalOtlpFileMetricExporter as ExperimentalOtlpFileMetricExporterConfig,
)
from opentelemetry.configuration.models import (
    ExperimentalPrometheusMetricExporter as PrometheusMetricExporterConfig,
)
from opentelemetry.configuration.models import (
    ExplicitBucketHistogramAggregation as ExplicitBucketConfig,
)
from opentelemetry.configuration.models import (
    ExporterDefaultHistogramAggregation,
    ExporterTemporalityPreference,
    IncludeExclude,
    InstrumentType,
    ViewSelector,
    ViewStream,
)
from opentelemetry.configuration.models import (
    MeterProvider as MeterProviderConfig,
)
from opentelemetry.configuration.models import (
    MetricReader as MetricReaderConfig,
)
from opentelemetry.configuration.models import (
    OtlpGrpcMetricExporter as OtlpGrpcMetricExporterConfig,
)
from opentelemetry.configuration.models import (
    OtlpHttpMetricExporter as OtlpHttpMetricExporterConfig,
)
from opentelemetry.configuration.models import (
    PeriodicMetricReader as PeriodicMetricReaderConfig,
)
from opentelemetry.configuration.models import (
    PullMetricExporter as PullMetricExporterConfig,
)
from opentelemetry.configuration.models import (
    PullMetricReader as PullMetricReaderConfig,
)
from opentelemetry.configuration.models import (
    PushMetricExporter as PushMetricExporterConfig,
)
from opentelemetry.configuration.models import (
    View as ViewConfig,
)
from opentelemetry.sdk.metrics import (
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
        self.assertEqual(len(provider._metric_readers), 0)

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
        reader = provider._metric_readers[0]
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
            "opentelemetry.configuration._meter_provider.metrics.set_meter_provider"
        ) as mock_set:
            configure_meter_provider(config)
            mock_set.assert_called_once()
            arg = mock_set.call_args[0][0]
            self.assertIsInstance(arg, MeterProvider)


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
        reader = provider._metric_readers[0]
        self.assertIsInstance(reader, PeriodicExportingMetricReader)
        self.assertIsInstance(reader._exporter, ConsoleMetricExporter)

    def test_null_valued_console_exporter_from_parsed_config(self):
        # Regression test for #5451: a dataclass-typed exporter written as
        # ``console:`` (present, null) must behave like ``console: {}`` rather
        # than requiring an explicit empty mapping.
        config = _dict_to_dataclass(
            {
                "readers": [
                    {"periodic": {"exporter": {"console": None}}},
                ]
            },
            MeterProviderConfig,
        )
        provider = create_meter_provider(config)
        reader = provider._metric_readers[0]
        self.assertIsInstance(reader, PeriodicExportingMetricReader)
        self.assertIsInstance(reader._exporter, ConsoleMetricExporter)

    def test_periodic_reader_default_interval(self):
        config = self._make_periodic_config(
            PushMetricExporterConfig(console=ConsoleMetricExporterConfig())
        )
        provider = create_meter_provider(config)
        reader = provider._metric_readers[0]
        self.assertEqual(reader._export_interval_millis, 60000.0)

    def test_periodic_reader_default_timeout(self):
        config = self._make_periodic_config(
            PushMetricExporterConfig(console=ConsoleMetricExporterConfig())
        )
        provider = create_meter_provider(config)
        reader = provider._metric_readers[0]
        self.assertEqual(reader._export_timeout_millis, 30000.0)

    def test_periodic_reader_explicit_interval(self):
        config = self._make_periodic_config(
            PushMetricExporterConfig(console=ConsoleMetricExporterConfig()),
            interval=5000,
        )
        provider = create_meter_provider(config)
        reader = provider._metric_readers[0]
        self.assertEqual(reader._export_interval_millis, 5000.0)

    def test_periodic_reader_explicit_timeout(self):
        config = self._make_periodic_config(
            PushMetricExporterConfig(console=ConsoleMetricExporterConfig()),
            timeout=10000,
        )
        provider = create_meter_provider(config)
        reader = provider._metric_readers[0]
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

    def test_otlp_file_development_missing_package_raises(self):
        config = self._make_periodic_config(
            PushMetricExporterConfig(
                otlp_file_development=ExperimentalOtlpFileMetricExporterConfig()
            )
        )
        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.json.file.metric_exporter": None,
            },
        ):
            with self.assertRaises(ConfigurationError) as ctx:
                create_meter_provider(config)
        self.assertIn(
            "opentelemetry-exporter-otlp-json-file", str(ctx.exception)
        )

    def test_otlp_file_development_default_stdout(self):
        mock_exporter_cls = MagicMock()
        mock_module = MagicMock()
        mock_module.FileMetricExporter = mock_exporter_cls

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.json.file.metric_exporter": mock_module,
            },
        ):
            config = self._make_periodic_config(
                PushMetricExporterConfig(
                    otlp_file_development=ExperimentalOtlpFileMetricExporterConfig()
                )
            )
            create_meter_provider(config)

        args, kwargs = mock_exporter_cls.call_args
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs["preferred_temporality"],
            {
                Counter: AggregationTemporality.CUMULATIVE,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.CUMULATIVE,
                ObservableCounter: AggregationTemporality.CUMULATIVE,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            },
        )
        self.assertIsInstance(
            kwargs["preferred_aggregation"][Histogram],
            ExplicitBucketHistogramAggregation,
        )

    def test_otlp_file_development_file_uri(self):
        mock_exporter_cls = MagicMock()
        mock_module = MagicMock()
        mock_module.FileMetricExporter = mock_exporter_cls

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.json.file.metric_exporter": mock_module,
            },
        ):
            config = self._make_periodic_config(
                PushMetricExporterConfig(
                    otlp_file_development=ExperimentalOtlpFileMetricExporterConfig(
                        output_stream="file:///tmp/metrics.jsonl"
                    )
                )
            )
            create_meter_provider(config)

        args, kwargs = mock_exporter_cls.call_args
        self.assertEqual(args, ("/tmp/metrics.jsonl",))
        self.assertIn("preferred_temporality", kwargs)
        self.assertIn("preferred_aggregation", kwargs)

    def test_otlp_file_development_unsupported_output_stream_raises(self):
        mock_exporter_cls = MagicMock()
        mock_module = MagicMock()
        mock_module.FileMetricExporter = mock_exporter_cls

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.exporter.otlp.json.file.metric_exporter": mock_module,
            },
        ):
            config = self._make_periodic_config(
                PushMetricExporterConfig(
                    otlp_file_development=ExperimentalOtlpFileMetricExporterConfig(
                        output_stream="http://example"
                    )
                )
            )
            with self.assertRaises(ConfigurationError) as ctx:
                create_meter_provider(config)
        self.assertIn("output_stream", str(ctx.exception))
        mock_exporter_cls.assert_not_called()


class TestCreatePullMetricReaders(unittest.TestCase):
    def test_pull_prometheus_creates_reader(self):
        mock_reader_cls = MagicMock()
        mock_start_server = MagicMock()
        mock_module = MagicMock()
        mock_module.PrometheusMetricReader = mock_reader_cls
        mock_module.start_http_server = mock_start_server

        with patch.dict(
            sys.modules,
            {"opentelemetry.exporter.prometheus": mock_module},
        ):
            config = MeterProviderConfig(
                readers=[
                    MetricReaderConfig(
                        pull=PullMetricReaderConfig(
                            exporter=PullMetricExporterConfig(
                                prometheus_development=PrometheusMetricExporterConfig(
                                    host="0.0.0.0",
                                    port=9090,
                                    target_info_enabled_development=False,
                                )
                            )
                        )
                    )
                ]
            )
            provider = create_meter_provider(config)

        mock_reader_cls.assert_called_once_with(disable_target_info=True)
        mock_start_server.assert_called_once_with(port=9090, addr="0.0.0.0")
        self.assertEqual(len(provider._metric_readers), 1)

    def test_pull_prometheus_defaults(self):
        mock_reader_cls = MagicMock()
        mock_start_server = MagicMock()
        mock_module = MagicMock()
        mock_module.PrometheusMetricReader = mock_reader_cls
        mock_module.start_http_server = mock_start_server

        with patch.dict(
            sys.modules,
            {"opentelemetry.exporter.prometheus": mock_module},
        ):
            config = MeterProviderConfig(
                readers=[
                    MetricReaderConfig(
                        pull=PullMetricReaderConfig(
                            exporter=PullMetricExporterConfig(
                                prometheus_development=PrometheusMetricExporterConfig()
                            )
                        )
                    )
                ]
            )
            provider = create_meter_provider(config)

        mock_reader_cls.assert_called_once_with(disable_target_info=False)
        mock_start_server.assert_called_once_with(port=9464, addr="localhost")
        self.assertEqual(len(provider._metric_readers), 1)

    def test_pull_prometheus_missing_package_raises(self):
        with patch.dict(
            sys.modules,
            {"opentelemetry.exporter.prometheus": None},
        ):
            config = MeterProviderConfig(
                readers=[
                    MetricReaderConfig(
                        pull=PullMetricReaderConfig(
                            exporter=PullMetricExporterConfig(
                                prometheus_development=PrometheusMetricExporterConfig()
                            )
                        )
                    )
                ]
            )
            with self.assertRaises(ConfigurationError):
                create_meter_provider(config)

    def test_pull_no_exporter_raises(self):
        config = MeterProviderConfig(
            readers=[
                MetricReaderConfig(
                    pull=PullMetricReaderConfig(
                        exporter=PullMetricExporterConfig()
                    )
                )
            ]
        )
        with self.assertRaises(ConfigurationError):
            create_meter_provider(config)

    def test_pull_plugin_loads_via_entry_point(self):
        mock_reader = MagicMock()
        mock_class = MagicMock(return_value=mock_reader)
        mock_entry_points = MagicMock(
            return_value=[MagicMock(**{"load.return_value": mock_class})]
        )
        with patch(
            "opentelemetry.configuration._common.entry_points",
            mock_entry_points,
        ):
            config = MeterProviderConfig(
                readers=[
                    MetricReaderConfig(
                        pull=PullMetricReaderConfig(
                            # pylint: disable=unexpected-keyword-arg
                            exporter=PullMetricExporterConfig(
                                my_custom_reader={"port": 8080}
                            )
                        )
                    )
                ]
            )
            provider = create_meter_provider(config)
        self.assertEqual(len(provider._metric_readers), 1)
        mock_class.assert_called_once_with(port=8080)
        mock_entry_points.assert_called_once_with(
            group="opentelemetry_pull_metric_exporter",
            name="my_custom_reader",
        )

    def test_pull_plugin_not_found_raises(self):
        with patch(
            "opentelemetry.configuration._common.entry_points",
            return_value=[],
        ):
            config = MeterProviderConfig(
                readers=[
                    MetricReaderConfig(
                        pull=PullMetricReaderConfig(
                            # pylint: disable=unexpected-keyword-arg
                            exporter=PullMetricExporterConfig(
                                no_such_reader={}
                            )
                        )
                    )
                ]
            )
            with self.assertRaises(ConfigurationError):
                create_meter_provider(config)

    def test_pull_producers_warns(self):
        mock_module = MagicMock()

        with patch.dict(
            sys.modules,
            {"opentelemetry.exporter.prometheus": mock_module},
        ):
            config = MeterProviderConfig(
                readers=[
                    MetricReaderConfig(
                        pull=PullMetricReaderConfig(
                            exporter=PullMetricExporterConfig(
                                prometheus_development=PrometheusMetricExporterConfig()
                            ),
                            producers=[MagicMock()],
                        )
                    )
                ]
            )
            with self.assertLogs(
                "opentelemetry.configuration._meter_provider",
                level="WARNING",
            ) as cm:
                create_meter_provider(config)
        self.assertTrue(any("MetricProducer" in msg for msg in cm.output))

    def test_pull_cardinality_limits_warns(self):
        mock_module = MagicMock()

        with patch.dict(
            sys.modules,
            {"opentelemetry.exporter.prometheus": mock_module},
        ):
            config = MeterProviderConfig(
                readers=[
                    MetricReaderConfig(
                        pull=PullMetricReaderConfig(
                            exporter=PullMetricExporterConfig(
                                prometheus_development=PrometheusMetricExporterConfig()
                            ),
                            cardinality_limits=MagicMock(),
                        )
                    )
                ]
            )
            with self.assertLogs(
                "opentelemetry.configuration._meter_provider",
                level="WARNING",
            ) as cm:
                create_meter_provider(config)
        self.assertTrue(any("cardinality_limits" in msg for msg in cm.output))


class TestCreateMetricReadersGeneral(unittest.TestCase):
    @staticmethod
    def _make_periodic_config(exporter_config):
        return MeterProviderConfig(
            readers=[
                MetricReaderConfig(
                    periodic=PeriodicMetricReaderConfig(
                        exporter=exporter_config
                    )
                )
            ]
        )

    def test_no_reader_type_raises(self):
        config = MeterProviderConfig(readers=[MetricReaderConfig()])
        with self.assertRaises(ConfigurationError):
            create_meter_provider(config)

    def test_no_exporter_type_raises(self):
        config = self._make_periodic_config(PushMetricExporterConfig())
        with self.assertRaises(ConfigurationError):
            create_meter_provider(config)

    def test_plugin_metric_exporter_loaded_via_entry_point(self):
        mock_exporter = MagicMock()
        mock_class = MagicMock(return_value=mock_exporter)
        with patch(
            "opentelemetry.configuration._common.entry_points",
            return_value=[MagicMock(**{"load.return_value": mock_class})],
        ):
            # pylint: disable=unexpected-keyword-arg
            config = self._make_periodic_config(
                PushMetricExporterConfig(my_custom_exporter={})
            )
            provider = create_meter_provider(config)
        self.assertEqual(len(provider._metric_readers), 1)

    def test_unknown_metric_exporter_raises_configuration_error(self):
        with patch(
            "opentelemetry.configuration._common.entry_points",
            return_value=[],
        ):
            # pylint: disable=unexpected-keyword-arg
            config = self._make_periodic_config(
                PushMetricExporterConfig(no_such_exporter={})
            )
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
        self.assertEqual(len(provider._metric_readers), 2)


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
        return provider._metric_readers[0]._exporter

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
            "opentelemetry.configuration._meter_provider", level="WARNING"
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

    def test_stream_aggregation_base2_exponential_record_min_max(self):
        for record_min_max, expected in [
            (True, True),
            (False, False),
            (None, True),
        ]:
            with self.subTest(record_min_max=record_min_max):
                view = self._get_view(
                    self._make_view_config(
                        stream_kwargs={
                            "aggregation": AggregationConfig(
                                base2_exponential_bucket_histogram=Base2Config(
                                    record_min_max=record_min_max
                                )
                            )
                        }
                    )
                )
                self.assertIsInstance(
                    view._aggregation, ExponentialBucketHistogramAggregation
                )
                self.assertEqual(view._aggregation._record_min_max, expected)

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
