"""Pure-Python equivalents of collector/metrics/v1/metrics_service_pb2.py.

Field numbers:
    ExportMetricsServiceRequest   resource_metrics=1
    ExportMetricsServiceResponse  (empty — no fields used in export path)
"""

from __future__ import annotations

from opentelemetry._proto.metrics.v1.metrics_pb2 import ResourceMetrics
from opentelemetry._proto._pyprotobuf.fields import msg


class ExportMetricsServiceRequest:
    def __init__(self, resource_metrics: list[ResourceMetrics] | None = None):
        self.resource_metrics: list[ResourceMetrics] = (
            list(resource_metrics) if resource_metrics else []
        )

    def SerializeToString(self) -> bytes:
        return b"".join(
            msg(1, rm.SerializeToString()) for rm in self.resource_metrics
        )


class ExportMetricsServiceResponse:
    @classmethod
    def FromString(cls, data: bytes) -> 'ExportMetricsServiceResponse':
        return cls()

    def SerializeToString(self) -> bytes:
        return b""
