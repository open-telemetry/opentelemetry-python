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

from time import sleep
from typing import Sequence
from unittest import TestCase

from opentelemetry.sdk.metrics.export import (
    InMemoryMetricExporter,
    MetricExportResult,
)


class MockMetric:
    # A placeholder class for mock metrics
    pass


class TestInMemoryMetricExporter(TestCase):
    def setUp(self):
        self.exporter = InMemoryMetricExporter()

    def test_initialization(self):
        self.assertIsInstance(self.exporter.metrics, dict)
        self.assertEqual(len(self.exporter.metrics), 0)
        self.assertEqual(self.exporter._counter, 0)

    def test_export(self):
        mock_metrics: Sequence[MockMetric] = [MockMetric(), MockMetric()]

        # Test the first export
        result = self.exporter.export(mock_metrics)
        self.assertEqual(result, MetricExportResult.SUCCESS)
        self.assertIn(0, self.exporter.metrics)
        self.assertEqual(self.exporter.metrics[0], mock_metrics)
        self.assertEqual(self.exporter._counter, 1)

        # Test the second export
        result = self.exporter.export(mock_metrics)
        self.assertEqual(result, MetricExportResult.SUCCESS)
        self.assertIn(1, self.exporter.metrics)
        self.assertEqual(self.exporter.metrics[1], mock_metrics)
        self.assertEqual(self.exporter._counter, 2)

    def test_force_flush(self):
        self.assertTrue(self.exporter.force_flush())
