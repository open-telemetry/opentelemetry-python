"""Pure-Python equivalents of collector/logs/v1/logs_service_pb2.py.

Field numbers:
    ExportLogsServiceRequest    resource_logs=1
    ExportLogsServiceResponse   (empty — no fields used in export path)
"""

from __future__ import annotations

from opentelemetry._proto.logs.v1.logs_pb2 import ResourceLogs
from opentelemetry._proto._pyprotobuf.fields import msg


class ExportLogsServiceRequest:
    def __init__(self, resource_logs: list[ResourceLogs] | None = None):
        self.resource_logs: list[ResourceLogs] = (
            list(resource_logs) if resource_logs else []
        )

    def SerializeToString(self) -> bytes:
        return b"".join(
            msg(1, rl.SerializeToString()) for rl in self.resource_logs
        )


class ExportLogsServiceResponse:
    @classmethod
    def FromString(cls, data: bytes) -> 'ExportLogsServiceResponse':
        return cls()

    def SerializeToString(self) -> bytes:
        return b""
