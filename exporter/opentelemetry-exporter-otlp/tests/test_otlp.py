# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0


from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    OTLPLogExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as HTTPSpanExporter,
)
from opentelemetry.test import TestCase


class TestOTLPExporters(TestCase):
    def test_constructors(self):
        for exporter in [
            OTLPSpanExporter,
            HTTPSpanExporter,
            OTLPLogExporter,
            OTLPMetricExporter,
        ]:
            with self.assertNotRaises(Exception):
                exporter()
