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

from unittest import TestCase

from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    OTLPLogExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    _otlp_metric_exporter_entrypoint,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk._configuration import _import_exporters


class TestEntrypoints(TestCase):
    def test_import_exporters(self) -> None:
        """
        Tests that the entrypoints can be loaded and don't have a typo in the names
        """
        (
            trace_exporters,
            metric_exporters,
            logs_exporters,
        ) = _import_exporters(
            trace_exporter_names=["otlp"],
            metric_exporter_names=["otlp"],
            log_exporter_names=["otlp"],
        )

        self.assertEqual(
            trace_exporters,
            {"otlp": OTLPSpanExporter},
        )
        self.assertEqual(
            metric_exporters,
            {"otlp": _otlp_metric_exporter_entrypoint},
        )
        self.assertEqual(
            logs_exporters,
            {"otlp": OTLPLogExporter},
        )
