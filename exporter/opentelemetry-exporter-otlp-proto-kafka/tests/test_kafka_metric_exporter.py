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


import unittest
from logging import ERROR, WARNING
from unittest.mock import Mock, create_autospec, patch

from kafka import KafkaProducer
from kafka.errors import InvalidRequiredAcksError, KafkaTimeoutError

from opentelemetry.exporter.otlp.proto.kafka._internal import metric_exporter
from opentelemetry.exporter.otlp.proto.kafka.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_KAFKA_METRICS_TOPIC,
)
from opentelemetry.sdk.metrics._internal.export import MetricExportResult


class TestOTLPMetricExporter(unittest.TestCase):
    def setUp(self):
        self.mock_producer = create_autospec(KafkaProducer)

    @patch.object(metric_exporter, "encode_metrics")
    def test_export(self, mock_encode_metrics):
        mock_spans = Mock()
        self.assertEqual(
            OTLPMetricExporter(producer=self.mock_producer).export(mock_spans),
            MetricExportResult.SUCCESS,
        )

        mock_encode_metrics.assert_called_once_with(mock_spans)
        self.mock_producer.send.assert_called_once_with(
            "otlp_metrics",
            value=mock_encode_metrics.return_value.SerializeToString.return_value,
            headers=[],
        )
        self.mock_producer.send.return_value.get.assert_called_once()

    @patch.dict(
        "os.environ",
        {OTEL_EXPORTER_KAFKA_METRICS_TOPIC: "metrics_topic"},
    )
    @patch.object(metric_exporter, "encode_metrics")
    def test_export_env_metrics_topic(self, mock_encode_logs):
        mock_spans = Mock()
        self.assertEqual(
            OTLPMetricExporter(producer=self.mock_producer).export(mock_spans),
            MetricExportResult.SUCCESS,
        )

        mock_encode_logs.assert_called_once_with(mock_spans)
        self.mock_producer.send.assert_called_once_with(
            "metrics_topic",
            value=mock_encode_logs.return_value.SerializeToString.return_value,
            headers=[],
        )
        self.mock_producer.send.return_value.get.assert_called_once_with(10)

    @patch.object(metric_exporter, "encode_metrics")
    def test_export_constructor_metrics_topic(self, mock_encode_logs):
        mock_spans = Mock()
        self.assertEqual(
            OTLPMetricExporter(
                producer=self.mock_producer, topic="metrics_topic"
            ).export(mock_spans),
            MetricExportResult.SUCCESS,
        )

        mock_encode_logs.assert_called_once_with(mock_spans)
        self.mock_producer.send.assert_called_once_with(
            "metrics_topic",
            value=mock_encode_logs.return_value.SerializeToString.return_value,
            headers=[],
        )
        self.mock_producer.send.return_value.get.assert_called_once_with(10)

    def test_shutdown(self):
        OTLPMetricExporter(producer=self.mock_producer).shutdown()

        self.mock_producer.close.assert_called_once()

    @patch.object(metric_exporter, "encode_metrics")
    def test_export_kafka_error(self, mock_encode_metrics):
        self.mock_producer.send.side_effect = InvalidRequiredAcksError()
        with self.assertLogs(level=ERROR) as error:
            self.assertEqual(
                OTLPMetricExporter(producer=self.mock_producer).export(Mock()),
                MetricExportResult.FAILURE,
            )
            self.assertIn(
                "Failed to export metrics batch reason:",
                error.records[0].message,
            )

    def test_export_post_shutdown_fails(self):
        exporter = OTLPMetricExporter(producer=self.mock_producer)
        exporter.shutdown()

        with self.assertLogs(level=WARNING) as warning:
            self.assertEqual(
                exporter.export(Mock()),
                MetricExportResult.FAILURE,
            )
            self.assertIn(
                "Exporter already shutdown, ignoring batch",
                warning.records[0].message,
            )

    def test_multiple_shutdown_warning(self):
        exporter = OTLPMetricExporter(producer=self.mock_producer)
        exporter.shutdown()

        with self.assertLogs(level=WARNING) as warning:
            exporter.shutdown()
            self.assertIn(
                "Exporter already shutdown, ignoring call",
                warning.records[0].message,
            )

    def test_force_flush(self):
        self.assertTrue(
            OTLPMetricExporter(producer=self.mock_producer).force_flush(),
        )

        self.mock_producer.flush.assert_called_once_with(10)

    def test_force_flush_timeout(self):
        self.mock_producer.flush.side_effect = KafkaTimeoutError()
        self.assertFalse(
            OTLPMetricExporter(producer=self.mock_producer).force_flush(),
        )
