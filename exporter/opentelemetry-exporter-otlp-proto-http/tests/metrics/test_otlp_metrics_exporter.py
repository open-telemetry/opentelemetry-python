# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=too-many-lines,protected-access,too-many-public-methods

import threading
import time
from logging import WARNING
from os import environ
from unittest import TestCase
from unittest.mock import Mock, patch

import requests
from mocket import Mocket, Mocketizer, mocketize
from mocket.mocks.mockhttp import Entry, Response

from opentelemetry.exporter.http.transport._requests import (
    RequestsHTTPTransport,
)
from opentelemetry.exporter.http.transport._urllib3 import (
    Urllib3HTTPTransport,
)
from opentelemetry.exporter.otlp.common._http import (
    Compression as CommonCompression,
)
from opentelemetry.exporter.otlp.proto.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    DEFAULT_ENDPOINT,
    DEFAULT_METRICS_EXPORT_PATH,
    OTLPMetricExporter,
    _get_split_resource_metrics_pb2,
    _split_metrics_data,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import (
    InstrumentationScope,
    KeyValue,
)
from opentelemetry.proto.metrics.v1 import metrics_pb2 as pb2
from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as Pb2Resource,
)
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_METRICS_CREDENTIAL_PROVIDER,
    OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
    OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED,
)
from opentelemetry.sdk.metrics import (
    Counter,
    Histogram,
    MeterProvider,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    InMemoryMetricReader,
    MetricExportResult,
    MetricsData,
    ResourceMetrics,
    ScopeMetrics,
)
from opentelemetry.sdk.metrics.view import (
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import (
    InstrumentationScope as SDKInstrumentationScope,
)
from opentelemetry.test.metrictestutil import _generate_sum
from opentelemetry.test.mock_test_classes import IterEntryPoint
from tests import _mock_clock

_TEST_ENDPOINT = "http://localhost:4318/v1/metrics"


def _decode_body(body: bytes) -> ExportMetricsServiceRequest:
    return ExportMetricsServiceRequest.FromString(body)


# pylint: disable=protected-access,too-many-public-methods
class TestOTLPMetricExporter(TestCase):
    def setUp(self):
        env_patcher = patch.dict("os.environ", {}, clear=True)
        env_patcher.start()
        self.addCleanup(env_patcher.stop)

        self.metric_reader = InMemoryMetricReader()
        self.meter_provider = MeterProvider(
            metric_readers=[self.metric_reader]
        )
        self.metrics = {
            "sum_int": MetricsData(
                resource_metrics=[
                    ResourceMetrics(
                        resource=Resource(
                            attributes={"a": 1, "b": False},
                            schema_url="resource_schema_url",
                        ),
                        scope_metrics=[
                            ScopeMetrics(
                                scope=SDKInstrumentationScope(
                                    name="first_name",
                                    version="first_version",
                                    schema_url="insrumentation_scope_schema_url",
                                ),
                                metrics=[_generate_sum("sum_int", 33)],
                                schema_url="instrumentation_scope_schema_url",
                            )
                        ],
                        schema_url="resource_schema_url",
                    )
                ]
            ),
        }

    def assert_standard_metric_attrs(self, attributes):
        self.assertEqual(
            attributes["otel.component.type"], "otlp_http_metric_exporter"
        )
        self.assertTrue(
            attributes["otel.component.name"].startswith(
                "otlp_http_metric_exporter/"
            )
        )
        self.assertEqual(attributes["server.address"], "localhost")
        self.assertEqual(attributes["server.port"], 4318)

    @staticmethod
    def _create_metrics_data_multiple_data_points(
        num_data_points: int,
    ) -> MetricsData:
        """Helper to create MetricsData with specified number of data points for testing batch splitting."""
        metrics = []
        for idx in range(num_data_points):
            metrics.append(_generate_sum(f"sum_int_{idx}", 33))

        return MetricsData(
            resource_metrics=[
                ResourceMetrics(
                    resource=Resource(
                        attributes={"a": 1, "b": False},
                        schema_url="resource_schema_url",
                    ),
                    scope_metrics=[
                        ScopeMetrics(
                            scope=SDKInstrumentationScope(
                                name="first_name",
                                version="first_version",
                                schema_url="insrumentation_scope_schema_url",
                            ),
                            metrics=metrics,
                            schema_url="instrumentation_scope_schema_url",
                        )
                    ],
                    schema_url="resource_schema_url",
                )
            ]
        )

    # -- construction / transport selection --------------------------------

    def test_constructor_default_uses_urllib3_transport(self):
        exporter = OTLPMetricExporter()

        self.assertEqual(
            exporter._endpoint, DEFAULT_ENDPOINT + DEFAULT_METRICS_EXPORT_PATH
        )
        self.assertIs(exporter._compression, CommonCompression.NONE)
        self.assertIsNone(exporter._session)
        self.assertIsInstance(exporter._client._transport, Urllib3HTTPTransport)

    def test_explicit_session_uses_requests_transport(self):
        session = requests.Session()
        exporter = OTLPMetricExporter(session=session)

        self.assertIs(exporter._session, session)
        self.assertIsInstance(
            exporter._client._transport, RequestsHTTPTransport
        )
        self.assertIs(exporter._client._transport._session, session)

    @patch("opentelemetry.exporter.otlp.proto.http._common.entry_points")
    def test_credential_provider_uses_requests_transport(
        self, mock_entry_point
    ):
        credential = requests.Session()
        mock_entry_point.configure_mock(
            return_value=[IterEntryPoint("custom_credential", lambda: credential)]
        )
        with patch.dict(
            environ,
            {
                _OTEL_PYTHON_EXPORTER_OTLP_HTTP_METRICS_CREDENTIAL_PROVIDER: "custom_credential",
            },
        ):
            exporter = OTLPMetricExporter()

        self.assertIs(exporter._session, credential)
        self.assertIsInstance(
            exporter._client._transport, RequestsHTTPTransport
        )

    @patch("opentelemetry.exporter.otlp.proto.http._common.entry_points")
    def test_exception_raised_when_entrypoint_returns_wrong_type(
        self, mock_entry_point
    ):
        mock_entry_point.configure_mock(
            return_value=[IterEntryPoint("bad_credential", lambda: 1)]
        )
        with (
            patch.dict(
                environ,
                {
                    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_METRICS_CREDENTIAL_PROVIDER: "bad_credential",
                },
            ),
            self.assertRaises(RuntimeError),
        ):
            OTLPMetricExporter()

    def test_compression_dual_enum_acceptance(self):
        for compression in (Compression.Gzip, CommonCompression.GZIP):
            with self.subTest(compression=compression):
                exporter = OTLPMetricExporter(compression=compression)
                self.assertIs(exporter._compression, CommonCompression.GZIP)

    def test_exporter_env_endpoint_without_slash(self):
        with patch.dict(
            environ, {OTEL_EXPORTER_OTLP_METRICS_ENDPOINT: "os.env.base"}
        ):
            exporter = OTLPMetricExporter()
        self.assertEqual(exporter._endpoint, "os.env.base")

    @mocketize
    def test_custom_transport(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        custom_transport = Urllib3HTTPTransport()

        with patch(
            "opentelemetry.exporter.otlp.proto.http.metric_exporter._build_transport"
        ) as mock_build_transport:
            exporter = OTLPMetricExporter(
                endpoint=_TEST_ENDPOINT, _transport=custom_transport
            )

        mock_build_transport.assert_not_called()
        self.assertIs(exporter._client._transport, custom_transport)

        result = exporter.export(self.metrics["sum_int"])
        self.assertEqual(result, MetricExportResult.SUCCESS)

    # -- export / wire format ------------------------------------------------

    @mocketize
    def test_serialization(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPMetricExporter(endpoint=_TEST_ENDPOINT)
        transport = exporter._client._transport

        with patch.object(
            transport, "request", wraps=transport.request
        ) as mock_request:
            self.assertEqual(
                exporter.export(self.metrics["sum_int"]),
                MetricExportResult.SUCCESS,
            )

        serialized_data = encode_metrics(self.metrics["sum_int"])
        sent_data = mock_request.call_args.kwargs["data"]
        self.assertEqual(_decode_body(sent_data), serialized_data)

    @patch.dict(
        "os.environ", {OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED: " true "}
    )
    @mocketize
    def test_success_records_metrics(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPMetricExporter(
            endpoint=_TEST_ENDPOINT, meter_provider=self.meter_provider
        )

        self.assertEqual(
            exporter.export(self.metrics["sum_int"]),
            MetricExportResult.SUCCESS,
        )

        metrics_data = self.metric_reader.get_metrics_data()
        scope_metrics = metrics_data.resource_metrics[0].scope_metrics[0]
        metrics = sorted(scope_metrics.metrics, key=lambda m: m.name)
        self.assertEqual(len(metrics), 3)
        names = [m.name for m in metrics]
        self.assertIn("otel.sdk.exporter.metric_data_point.exported", names)
        self.assertIn("otel.sdk.exporter.metric_data_point.inflight", names)
        self.assertIn("otel.sdk.exporter.operation.duration", names)
        for metric in metrics:
            self.assert_standard_metric_attrs(
                metric.data.data_points[0].attributes
            )

    @patch.dict(
        "os.environ", {OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED: "true"}
    )
    @mocketize
    def test_failure_records_metrics(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=401)
        exporter = OTLPMetricExporter(
            endpoint=_TEST_ENDPOINT, meter_provider=self.meter_provider
        )

        self.assertEqual(
            exporter.export(self.metrics["sum_int"]),
            MetricExportResult.FAILURE,
        )

        metrics_data = self.metric_reader.get_metrics_data()
        scope_metrics = metrics_data.resource_metrics[0].scope_metrics[0]
        metrics = sorted(scope_metrics.metrics, key=lambda m: m.name)
        duration_metric = next(
            m
            for m in metrics
            if m.name == "otel.sdk.exporter.operation.duration"
        )
        self.assertEqual(
            duration_metric.data.data_points[0].attributes[
                "http.response.status_code"
            ],
            401,
        )

    # -- batch splitting integration ------------------------------------------

    @mocketize
    def test_export_max_export_batch_size_single_batch_integration(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)

        # 2 data points, batch size of 3: fits in one batch
        metrics_data = self._create_metrics_data_multiple_data_points(2)
        exporter = OTLPMetricExporter(
            endpoint=_TEST_ENDPOINT, max_export_batch_size=3
        )
        transport = exporter._client._transport

        with patch.object(
            transport, "request", wraps=transport.request
        ) as mock_request:
            result = exporter.export(metrics_data)

        self.assertEqual(result, MetricExportResult.SUCCESS)
        self.assertEqual(mock_request.call_count, 1)

        request = _decode_body(mock_request.call_args.kwargs["data"])
        self.assertEqual(len(request.resource_metrics), 1)
        metrics = request.resource_metrics[0].scope_metrics[0].metrics
        metric_names = {metric.name for metric in metrics}
        self.assertEqual(metric_names, {"sum_int_0", "sum_int_1"})

    @mocketize
    def test_export_max_export_batch_size_multiple_batches_integration(self):
        Entry.register(
            Entry.POST,
            _TEST_ENDPOINT,
            Response(status=200),
            Response(status=200),
        )

        # 3 data points, batch size of 2: requires 2 batches
        metrics_data = self._create_metrics_data_multiple_data_points(3)
        exporter = OTLPMetricExporter(
            endpoint=_TEST_ENDPOINT, max_export_batch_size=2
        )
        transport = exporter._client._transport

        with patch.object(
            transport, "request", wraps=transport.request
        ) as mock_request:
            result = exporter.export(metrics_data)

        self.assertEqual(result, MetricExportResult.SUCCESS)
        self.assertEqual(mock_request.call_count, 2)

        first_request = _decode_body(
            mock_request.call_args_list[0].kwargs["data"]
        )
        first_metrics = first_request.resource_metrics[0].scope_metrics[0].metrics
        self.assertEqual(
            {m.name for m in first_metrics}, {"sum_int_0", "sum_int_1"}
        )

        second_request = _decode_body(
            mock_request.call_args_list[1].kwargs["data"]
        )
        second_metrics = second_request.resource_metrics[0].scope_metrics[0].metrics
        self.assertEqual(len(second_metrics), 1)
        self.assertEqual(second_metrics[0].name, "sum_int_2")

    @mocketize
    def test_export_max_export_batch_size_retry_scenarios_integration(self):
        Entry.register(
            Entry.POST,
            _TEST_ENDPOINT,
            Response(status=200),
            Response(status=400),
        )

        # 3 data points, batch size of 2: requires 2 batches
        metrics_data = self._create_metrics_data_multiple_data_points(3)
        exporter = OTLPMetricExporter(
            endpoint=_TEST_ENDPOINT, max_export_batch_size=2
        )

        result = exporter.export(metrics_data)
        self.assertEqual(result, MetricExportResult.FAILURE)
        self.assertEqual(len(Mocket.request_list()), 2)

    @mocketize
    def test_export_max_export_batch_size_retryable_failure_integration(self):
        Entry.register(
            Entry.POST,
            _TEST_ENDPOINT,
            Response(status=200),
            Response(status=503),
            Response(status=200),
        )

        # 3 data points, batch size of 2: requires 2 batches
        metrics_data = self._create_metrics_data_multiple_data_points(3)
        exporter = OTLPMetricExporter(
            endpoint=_TEST_ENDPOINT, max_export_batch_size=2, timeout=2.0
        )

        result = exporter.export(metrics_data)
        self.assertEqual(result, MetricExportResult.SUCCESS)
        # First batch + retry of second batch
        self.assertEqual(len(Mocket.request_list()), 3)

    # -- aggregation / temporality (unchanged pure logic) ---------------------

    def test_aggregation_temporality(self):
        otlp_metric_exporter = OTLPMetricExporter()

        for (
            temporality
        ) in otlp_metric_exporter._preferred_temporality.values():
            self.assertEqual(temporality, AggregationTemporality.CUMULATIVE)

        with patch.dict(
            environ,
            {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "CUMULATIVE"},
        ):
            otlp_metric_exporter = OTLPMetricExporter()

            for (
                temporality
            ) in otlp_metric_exporter._preferred_temporality.values():
                self.assertEqual(
                    temporality, AggregationTemporality.CUMULATIVE
                )

        with patch.dict(
            environ, {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "ABC"}
        ):
            with self.assertLogs(level=WARNING):
                otlp_metric_exporter = OTLPMetricExporter()

            for (
                temporality
            ) in otlp_metric_exporter._preferred_temporality.values():
                self.assertEqual(
                    temporality, AggregationTemporality.CUMULATIVE
                )

        with patch.dict(
            environ,
            {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "DELTA"},
        ):
            otlp_metric_exporter = OTLPMetricExporter()

            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[Counter],
                AggregationTemporality.DELTA,
            )
            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[UpDownCounter],
                AggregationTemporality.CUMULATIVE,
            )
            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[Histogram],
                AggregationTemporality.DELTA,
            )
            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[ObservableCounter],
                AggregationTemporality.DELTA,
            )
            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[
                    ObservableUpDownCounter
                ],
                AggregationTemporality.CUMULATIVE,
            )
            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[ObservableGauge],
                AggregationTemporality.CUMULATIVE,
            )

        with patch.dict(
            environ,
            {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "LOWMEMORY"},
        ):
            otlp_metric_exporter = OTLPMetricExporter()

            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[Counter],
                AggregationTemporality.DELTA,
            )
            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[UpDownCounter],
                AggregationTemporality.CUMULATIVE,
            )
            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[Histogram],
                AggregationTemporality.DELTA,
            )
            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[ObservableCounter],
                AggregationTemporality.CUMULATIVE,
            )
            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[
                    ObservableUpDownCounter
                ],
                AggregationTemporality.CUMULATIVE,
            )
            self.assertEqual(
                otlp_metric_exporter._preferred_temporality[ObservableGauge],
                AggregationTemporality.CUMULATIVE,
            )

    def test_exponential_explicit_bucket_histogram(self):
        self.assertIsInstance(
            OTLPMetricExporter()._preferred_aggregation[Histogram],
            ExplicitBucketHistogramAggregation,
        )

        with patch.dict(
            environ,
            {
                OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION: "base2_exponential_bucket_histogram"
            },
        ):
            self.assertIsInstance(
                OTLPMetricExporter()._preferred_aggregation[Histogram],
                ExponentialBucketHistogramAggregation,
            )

        with patch.dict(
            environ,
            {OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION: "abc"},
        ):
            with self.assertLogs(level=WARNING) as log:
                self.assertIsInstance(
                    OTLPMetricExporter()._preferred_aggregation[Histogram],
                    ExplicitBucketHistogramAggregation,
                )
            self.assertIn(
                (
                    "Invalid value for OTEL_EXPORTER_OTLP_METRICS_DEFAULT_"
                    "HISTOGRAM_AGGREGATION: ABC, using explicit bucket "
                    "histogram aggregation"
                ),
                log.output[0],
            )

        with patch.dict(
            environ,
            {
                OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION: "explicit_bucket_histogram"
            },
        ):
            self.assertIsInstance(
                OTLPMetricExporter()._preferred_aggregation[Histogram],
                ExplicitBucketHistogramAggregation,
            )

    def test_preferred_aggregation_override(self):
        histogram_aggregation = ExplicitBucketHistogramAggregation(
            boundaries=[0.05, 0.1, 0.5, 1, 5, 10],
        )

        exporter = OTLPMetricExporter(
            preferred_aggregation={
                Histogram: histogram_aggregation,
            },
        )

        self.assertEqual(
            exporter._preferred_aggregation[Histogram], histogram_aggregation
        )

    # -- misc -----------------------------------------------------------------

    @mocketize
    def test_2xx_status_code(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        self.assertEqual(
            OTLPMetricExporter(endpoint=_TEST_ENDPOINT).export(
                self.metrics["sum_int"]
            ),
            MetricExportResult.SUCCESS,
        )

    @mocketize
    def test_exporter_metrics_disabled_after_set_meter_provider(self):
        Entry.single_register(Entry.POST, _TEST_ENDPOINT, status=200)
        exporter = OTLPMetricExporter(endpoint=_TEST_ENDPOINT)
        exporter.set_meter_provider(self.meter_provider)

        self.assertEqual(
            exporter.export(self.metrics["sum_int"]),
            MetricExportResult.SUCCESS,
        )

        self.assertIsNone(self.metric_reader.get_metrics_data())

    def test_export_retryable_status_codes(self):
        for status_code in (429, 502, 503, 504):
            with self.subTest(status_code=status_code), Mocketizer():
                Entry.register(
                    Entry.POST,
                    _TEST_ENDPOINT,
                    Response(status=status_code),
                    Response(status=200),
                )
                exporter = OTLPMetricExporter(
                    endpoint=_TEST_ENDPOINT, timeout=30.0
                )
                shutdown_event = Mock(spec=threading.Event)
                shutdown_event.is_set.return_value = False
                exporter._client._shutdown_event = shutdown_event

                with _mock_clock(shutdown_event):
                    result = exporter.export(self.metrics["sum_int"])

                self.assertEqual(result, MetricExportResult.SUCCESS)
                self.assertEqual(len(Mocket.request_list()), 2)

    def test_export_non_retryable_status_codes(self):
        for status_code in (400, 401, 403, 404, 408, 500, 501):
            with self.subTest(status_code=status_code), Mocketizer():
                Entry.single_register(
                    Entry.POST, _TEST_ENDPOINT, status=status_code
                )
                exporter = OTLPMetricExporter(endpoint=_TEST_ENDPOINT)

                result = exporter.export(self.metrics["sum_int"])

                self.assertEqual(result, MetricExportResult.FAILURE)
                self.assertEqual(len(Mocket.request_list()), 1)

    @mocketize
    def test_shutdown_interrupts_retry_backoff(self):
        Entry.register(
            Entry.POST,
            _TEST_ENDPOINT,
            *[Response(status=503)] * 6,
        )
        exporter = OTLPMetricExporter(endpoint=_TEST_ENDPOINT, timeout=1.5)
        thread = threading.Thread(
            target=exporter.export, args=(self.metrics["sum_int"],)
        )
        before = time.time()
        thread.start()
        time.sleep(0.05)
        exporter.shutdown()
        thread.join()
        after = time.time()

        self.assertLess(after - before, 0.5)

    # -- split_metrics_data / get_split_resource_metrics_pb2 (unchanged) ------

    def test_split_metrics_data_many_data_points(self):
        metrics_data = ExportMetricsServiceRequest(
            resource_metrics=[
                _resource_metrics(
                    index=1,
                    scope_metrics=[
                        _scope_metrics(
                            index=1,
                            metrics=[
                                _gauge(
                                    index=1,
                                    data_points=[
                                        _number_data_point(11),
                                        _number_data_point(12),
                                        _number_data_point(13),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )
        split_metrics_data: list[ExportMetricsServiceRequest] = list(
            _split_metrics_data(
                metrics_data=metrics_data,
                max_export_batch_size=2,
            )
        )

        self.assertEqual(
            [
                ExportMetricsServiceRequest(
                    resource_metrics=[
                        _resource_metrics(
                            index=1,
                            scope_metrics=[
                                _scope_metrics(
                                    index=1,
                                    metrics=[
                                        _gauge(
                                            index=1,
                                            data_points=[
                                                _number_data_point(11),
                                                _number_data_point(12),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ]
                ),
                ExportMetricsServiceRequest(
                    resource_metrics=[
                        _resource_metrics(
                            index=1,
                            scope_metrics=[
                                _scope_metrics(
                                    index=1,
                                    metrics=[
                                        _gauge(
                                            index=1,
                                            data_points=[
                                                _number_data_point(13),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ]
                ),
            ],
            split_metrics_data,
        )

    def test_split_metrics_data_nb_data_points_equal_batch_size(self):
        metrics_data = ExportMetricsServiceRequest(
            resource_metrics=[
                _resource_metrics(
                    index=1,
                    scope_metrics=[
                        _scope_metrics(
                            index=1,
                            metrics=[
                                _gauge(
                                    index=1,
                                    data_points=[
                                        _number_data_point(11),
                                        _number_data_point(12),
                                        _number_data_point(13),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )

        split_metrics_data: list[ExportMetricsServiceRequest] = list(
            _split_metrics_data(
                metrics_data=metrics_data,
                max_export_batch_size=3,
            )
        )

        self.assertEqual(
            [
                ExportMetricsServiceRequest(
                    resource_metrics=[
                        _resource_metrics(
                            index=1,
                            scope_metrics=[
                                _scope_metrics(
                                    index=1,
                                    metrics=[
                                        _gauge(
                                            index=1,
                                            data_points=[
                                                _number_data_point(11),
                                                _number_data_point(12),
                                                _number_data_point(13),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ]
                ),
            ],
            split_metrics_data,
        )

    def test_split_metrics_data_many_resources_scopes_metrics(self):
        metrics_data = ExportMetricsServiceRequest(
            resource_metrics=[
                _resource_metrics(
                    index=1,
                    scope_metrics=[
                        _scope_metrics(
                            index=1,
                            metrics=[
                                _gauge(
                                    index=1,
                                    data_points=[
                                        _number_data_point(11),
                                    ],
                                ),
                                _gauge(
                                    index=2,
                                    data_points=[
                                        _number_data_point(12),
                                    ],
                                ),
                            ],
                        ),
                        _scope_metrics(
                            index=2,
                            metrics=[
                                _gauge(
                                    index=3,
                                    data_points=[
                                        _number_data_point(13),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                _resource_metrics(
                    index=2,
                    scope_metrics=[
                        _scope_metrics(
                            index=3,
                            metrics=[
                                _gauge(
                                    index=4,
                                    data_points=[
                                        _number_data_point(14),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )

        split_metrics_data: list[ExportMetricsServiceRequest] = list(
            _split_metrics_data(
                metrics_data=metrics_data,
                max_export_batch_size=2,
            )
        )

        self.assertEqual(
            [
                ExportMetricsServiceRequest(
                    resource_metrics=[
                        _resource_metrics(
                            index=1,
                            scope_metrics=[
                                _scope_metrics(
                                    index=1,
                                    metrics=[
                                        _gauge(
                                            index=1,
                                            data_points=[
                                                _number_data_point(11),
                                            ],
                                        ),
                                        _gauge(
                                            index=2,
                                            data_points=[
                                                _number_data_point(12),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ]
                ),
                ExportMetricsServiceRequest(
                    resource_metrics=[
                        _resource_metrics(
                            index=1,
                            scope_metrics=[
                                _scope_metrics(
                                    index=2,
                                    metrics=[
                                        _gauge(
                                            index=3,
                                            data_points=[
                                                _number_data_point(13),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        _resource_metrics(
                            index=2,
                            scope_metrics=[
                                _scope_metrics(
                                    index=3,
                                    metrics=[
                                        _gauge(
                                            index=4,
                                            data_points=[
                                                _number_data_point(14),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ]
                ),
            ],
            split_metrics_data,
        )

    def test_get_split_resource_metrics_pb2_one_of_each(self):
        split_resource_metrics = [
            {
                "resource": Pb2Resource(
                    attributes=[
                        KeyValue(key="foo", value={"string_value": "bar"})
                    ],
                ),
                "schema_url": "http://foo-bar",
                "scope_metrics": [
                    {
                        "scope": InstrumentationScope(
                            name="foo-scope", version="1.0.0"
                        ),
                        "schema_url": "http://foo-baz",
                        "metrics": [
                            {
                                "name": "foo-metric",
                                "description": "foo-description",
                                "unit": "foo-unit",
                                "sum": {
                                    "aggregation_temporality": 1,
                                    "is_monotonic": True,
                                    "data_points": [
                                        pb2.NumberDataPoint(
                                            attributes=[
                                                KeyValue(
                                                    key="dp_key",
                                                    value={
                                                        "string_value": "dp_value"
                                                    },
                                                )
                                            ],
                                            start_time_unix_nano=12345,
                                            time_unix_nano=12350,
                                            as_double=42.42,
                                        )
                                    ],
                                },
                            }
                        ],
                    }
                ],
            }
        ]

        result = _get_split_resource_metrics_pb2(split_resource_metrics)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], pb2.ResourceMetrics)
        self.assertEqual(result[0].schema_url, "http://foo-bar")
        self.assertEqual(len(result[0].scope_metrics), 1)
        self.assertEqual(result[0].scope_metrics[0].scope.name, "foo-scope")
        self.assertEqual(len(result[0].scope_metrics[0].metrics), 1)
        self.assertEqual(
            result[0].scope_metrics[0].metrics[0].name, "foo-metric"
        )
        self.assertEqual(
            result[0].scope_metrics[0].metrics[0].sum.is_monotonic, True
        )

    def test_get_split_resource_metrics_pb2_multiples(self):
        split_resource_metrics = [
            {
                "resource": Pb2Resource(
                    attributes=[
                        KeyValue(key="foo1", value={"string_value": "bar2"})
                    ],
                ),
                "schema_url": "http://foo-bar-1",
                "scope_metrics": [
                    {
                        "scope": InstrumentationScope(
                            name="foo-scope-1", version="1.0.0"
                        ),
                        "schema_url": "http://foo-baz-1",
                        "metrics": [
                            {
                                "name": "foo-metric-1",
                                "description": "foo-description-1",
                                "unit": "foo-unit-1",
                                "gauge": {
                                    "data_points": [
                                        pb2.NumberDataPoint(
                                            attributes=[
                                                KeyValue(
                                                    key="dp_key",
                                                    value={
                                                        "string_value": "dp_value"
                                                    },
                                                )
                                            ],
                                            start_time_unix_nano=12345,
                                            time_unix_nano=12350,
                                            as_double=42.42,
                                        )
                                    ],
                                },
                            }
                        ],
                    }
                ],
            },
            {
                "resource": Pb2Resource(
                    attributes=[
                        KeyValue(key="foo2", value={"string_value": "bar2"})
                    ],
                ),
                "schema_url": "http://foo-bar-2",
                "scope_metrics": [
                    {
                        "scope": InstrumentationScope(
                            name="foo-scope-2", version="2.0.0"
                        ),
                        "schema_url": "http://foo-baz-2",
                        "metrics": [
                            {
                                "name": "foo-metric-2",
                                "description": "foo-description-2",
                                "unit": "foo-unit-2",
                                "histogram": {
                                    "aggregation_temporality": 2,
                                    "data_points": [
                                        pb2.HistogramDataPoint(
                                            attributes=[
                                                KeyValue(
                                                    key="dp_key",
                                                    value={
                                                        "string_value": "dp_value"
                                                    },
                                                )
                                            ],
                                            start_time_unix_nano=12345,
                                            time_unix_nano=12350,
                                        )
                                    ],
                                },
                            }
                        ],
                    }
                ],
            },
        ]

        result = _get_split_resource_metrics_pb2(split_resource_metrics)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].schema_url, "http://foo-bar-1")
        self.assertEqual(result[1].schema_url, "http://foo-bar-2")
        self.assertEqual(len(result[0].scope_metrics), 1)
        self.assertEqual(len(result[1].scope_metrics), 1)
        self.assertEqual(result[0].scope_metrics[0].scope.name, "foo-scope-1")
        self.assertEqual(result[1].scope_metrics[0].scope.name, "foo-scope-2")
        self.assertEqual(
            result[0].scope_metrics[0].metrics[0].name, "foo-metric-1"
        )
        self.assertEqual(
            result[1].scope_metrics[0].metrics[0].name, "foo-metric-2"
        )

    def test_get_split_resource_metrics_pb2_unsupported_metric_type(self):
        split_resource_metrics = [
            {
                "resource": Pb2Resource(
                    attributes=[
                        KeyValue(key="foo", value={"string_value": "bar"})
                    ],
                ),
                "schema_url": "http://foo-bar",
                "scope_metrics": [
                    {
                        "scope": InstrumentationScope(
                            name="foo", version="1.0.0"
                        ),
                        "schema_url": "http://foo-baz",
                        "metrics": [
                            {
                                "name": "unsupported-metric",
                                "description": "foo-bar",
                                "unit": "foo-bar",
                                "unsupported_metric_type": {},
                            }
                        ],
                    }
                ],
            }
        ]

        with self.assertLogs(level="WARNING") as log:
            result = _get_split_resource_metrics_pb2(split_resource_metrics)
        self.assertEqual(len(result), 1)
        self.assertIn(
            "Tried to split and export an unsupported metric type",
            log.output[0],
        )


def _resource_metrics(
    index: int, scope_metrics: list[pb2.ScopeMetrics]
) -> pb2.ResourceMetrics:
    return pb2.ResourceMetrics(
        resource={
            "attributes": [KeyValue(key="a", value={"int_value": index})],
        },
        schema_url=f"resource_url_{index}",
        scope_metrics=scope_metrics,
    )


def _scope_metrics(index: int, metrics: list[pb2.Metric]) -> pb2.ScopeMetrics:
    return pb2.ScopeMetrics(
        scope=InstrumentationScope(name=f"scope_{index}"),
        schema_url=f"scope_url_{index}",
        metrics=metrics,
    )


def _gauge(index: int, data_points: list[pb2.NumberDataPoint]) -> pb2.Metric:
    return pb2.Metric(
        name=f"gauge_{index}",
        description="description",
        unit="unit",
        gauge=pb2.Gauge(data_points=data_points),
    )


def _number_data_point(value: int) -> pb2.NumberDataPoint:
    return pb2.NumberDataPoint(
        attributes=[
            KeyValue(key="a", value={"int_value": 1}),
            KeyValue(key="b", value={"bool_value": True}),
        ],
        start_time_unix_nano=1641946015139533244,
        time_unix_nano=1641946016139533244,
        as_int=value,
    )
