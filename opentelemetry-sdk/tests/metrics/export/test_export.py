# Copyright 2019, OpenTelemetry Authors
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
from unittest import mock

from opentelemetry.sdk import metrics
from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter


class TestConsoleMetricsExporter(unittest.TestCase):
    # pylint: disable=no-self-use
    def test_export(self):
        meter = metrics.Meter()
        exporter = ConsoleMetricsExporter()
        metric = metrics.Counter(
            "available memory",
            "available memory",
            "bytes",
            int,
            meter,
            ("environment",),
        )
        kvp = {"environment": "staging"}
        label_set = meter.get_label_set(kvp)
        handle = metric.get_handle(label_set)
        result = '{}(data="{}", label_values="{}", metric_data={})'.format(
            ConsoleMetricsExporter.__name__, metric, label_set, handle
        )
        with mock.patch("sys.stdout") as mock_stdout:
            exporter.export([(metric, label_set)])
            mock_stdout.write.assert_any_call(result)
