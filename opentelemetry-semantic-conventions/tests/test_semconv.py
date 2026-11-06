# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
# type: ignore

from importlib.util import find_spec
from unittest import TestCase
from unittest.mock import Mock

from opentelemetry.semconv._incubating.metrics.otel_metrics import (
    create_otel_sdk_exporter_operation_duration,
    create_otel_sdk_metric_reader_collection_duration,
)


class TestSemanticConventions(TestCase):
    def test_semantic_conventions(self):
        if find_spec("opentelemetry.semconv") is None:
            self.fail("opentelemetry-semantic-conventions not installed")

    def test_create_otel_sdk_exporter_operation_duration(self):
        meter = Mock()
        create_otel_sdk_exporter_operation_duration(meter)
        meter.create_histogram.assert_called_once_with(
            name="otel.sdk.exporter.operation.duration",
            description="The duration of exporting a batch of telemetry records.",
            unit="s",
            explicit_bucket_boundaries_advisory=[],
        )

    def test_create_otel_sdk_metric_reader_collection_duration(self):
        meter = Mock()
        create_otel_sdk_metric_reader_collection_duration(meter)
        meter.create_histogram.assert_called_once_with(
            name="otel.sdk.metric_reader.collection.duration",
            description="The duration of the collect operation of the metric reader.",
            unit="s",
            explicit_bucket_boundaries_advisory=[],
        )
