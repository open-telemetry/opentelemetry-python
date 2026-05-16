# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import json
import unittest
from unittest.mock import patch

from opentelemetry.exporter.otlp.json.file._internal import (
    _format_line,
    _get_aggregation,
    _get_temporality,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION,
    OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
)
from opentelemetry.sdk.metrics import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics.export import AggregationTemporality
from opentelemetry.sdk.metrics.view import (
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
)

_LOGGER_NAME = "opentelemetry.exporter.otlp.json.file._internal"


class TestFormatLine(unittest.TestCase):
    def test_produces_valid_json(self):
        result = _format_line({"a": 1, "b": "hello"})
        parsed = json.loads(result.strip())
        self.assertEqual(parsed, {"a": 1, "b": "hello"})

    def test_newline_terminated(self):
        result = _format_line({"x": 0})
        self.assertTrue(result.endswith("\n"))

    def test_compact_no_spaces(self):
        result = _format_line({"a": 1, "b": 2})
        self.assertNotIn(" ", result)

    def test_nested_structure(self):
        entry = {"outer": {"inner": [1, 2, 3]}, "flag": True}
        result = _format_line(entry)
        parsed = json.loads(result.strip())
        self.assertEqual(parsed, entry)


class TestGetTemporality(unittest.TestCase):
    def test_temporality_default_is_cumulative(self):
        result = _get_temporality(None)
        for instrument_class in (
            Counter,
            UpDownCounter,
            Histogram,
            ObservableCounter,
            ObservableUpDownCounter,
            ObservableGauge,
        ):
            with self.subTest(instrument=instrument_class.__name__):
                self.assertEqual(
                    result[instrument_class],
                    AggregationTemporality.CUMULATIVE,
                )

    def test_temporality_delta_env(self):
        delta_cases = {
            Counter: AggregationTemporality.DELTA,
            UpDownCounter: AggregationTemporality.CUMULATIVE,
            Histogram: AggregationTemporality.DELTA,
            ObservableCounter: AggregationTemporality.DELTA,
            ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
            ObservableGauge: AggregationTemporality.CUMULATIVE,
        }
        with patch.dict(
            "os.environ",
            {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "DELTA"},
        ):
            result = _get_temporality(None)
        for instrument_class, expected in delta_cases.items():
            with self.subTest(instrument=instrument_class.__name__):
                self.assertEqual(result[instrument_class], expected)

    def test_temporality_lowmemory_env(self):
        lowmemory_cases = {
            Counter: AggregationTemporality.DELTA,
            UpDownCounter: AggregationTemporality.CUMULATIVE,
            Histogram: AggregationTemporality.DELTA,
            ObservableCounter: AggregationTemporality.CUMULATIVE,
            ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
            ObservableGauge: AggregationTemporality.CUMULATIVE,
        }
        with patch.dict(
            "os.environ",
            {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "LOWMEMORY"},
        ):
            result = _get_temporality(None)
        for instrument_class, expected in lowmemory_cases.items():
            with self.subTest(instrument=instrument_class.__name__):
                self.assertEqual(result[instrument_class], expected)

    def test_temporality_invalid_env_logs_warning(self):
        with patch.dict(
            "os.environ",
            {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "INVALID"},
        ):
            with self.assertLogs(_LOGGER_NAME, level="WARNING"):
                result = _get_temporality(None)
        self.assertEqual(
            result[Counter],
            AggregationTemporality.CUMULATIVE,
        )

    def test_temporality_override_takes_precedence(self):
        with patch.dict(
            "os.environ",
            {OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: "CUMULATIVE"},
        ):
            result = _get_temporality({Counter: AggregationTemporality.DELTA})
        self.assertEqual(result[Counter], AggregationTemporality.DELTA)


class TestGetAggregation(unittest.TestCase):
    def test_aggregation_default_is_explicit_bucket(self):
        result = _get_aggregation(None)
        self.assertIsInstance(
            result[Histogram],
            ExplicitBucketHistogramAggregation,
        )

    def test_aggregation_exponential_env(self):
        with patch.dict(
            "os.environ",
            {
                OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION: "base2_exponential_bucket_histogram"
            },
        ):
            result = _get_aggregation(None)
        self.assertIsInstance(
            result[Histogram],
            ExponentialBucketHistogramAggregation,
        )

    def test_aggregation_invalid_env_logs_warning(self):
        with patch.dict(
            "os.environ",
            {
                OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION: "unknown_aggregation"
            },
        ):
            with self.assertLogs(_LOGGER_NAME, level="WARNING"):
                result = _get_aggregation(None)
        self.assertIsInstance(
            result[Histogram],
            ExplicitBucketHistogramAggregation,
        )

    def test_aggregation_override_takes_precedence(self):
        custom_aggregation = ExponentialBucketHistogramAggregation()
        with patch.dict(
            "os.environ",
            {
                OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION: "explicit_bucket_histogram"
            },
        ):
            result = _get_aggregation({Histogram: custom_aggregation})
        self.assertIs(result[Histogram], custom_aggregation)
