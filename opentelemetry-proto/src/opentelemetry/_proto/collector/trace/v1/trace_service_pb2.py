"""Pure-Python equivalents of collector/trace/v1/trace_service_pb2.py.

Field numbers:
    ExportTraceServiceRequest   resource_spans=1
    ExportTraceServiceResponse  (empty — no fields used in export path)
"""

from __future__ import annotations

from opentelemetry._proto.trace.v1.trace_pb2 import ResourceSpans
from opentelemetry._proto._pyprotobuf.fields import msg


class ExportTraceServiceRequest:
    def __init__(self, resource_spans: list[ResourceSpans] | None = None):
        self.resource_spans: list[ResourceSpans] = (
            list(resource_spans) if resource_spans else []
        )

    def SerializeToString(self) -> bytes:
        return b"".join(
            msg(1, rs.SerializeToString()) for rs in self.resource_spans
        )


class ExportTraceServiceResponse:
    @classmethod
    def FromString(cls, data: bytes) -> 'ExportTraceServiceResponse':
        return cls()

    def SerializeToString(self) -> bytes:
        return b""
