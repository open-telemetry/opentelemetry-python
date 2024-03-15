import typing
from enum import Enum

import grpc

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.trace.export.experimental.client import GrpcClientABC, RetryingGrpcClient, GrpcClient


class ExporterFlushResult(Enum):
    SUCCESS = 1
    FAILURE = 2
    TIMEOUT = 3


class OTLPSpanExporter2(SpanExporter):
    """
    An implementation of SpanExporter. Accepts an optional client. If one is not supplied, creates a retrying client.
    Sends spans immediately -- has no queue to flush or separate thread to shut down.
    """

    def __init__(self, client: GrpcClientABC = RetryingGrpcClient(GrpcClient())):
        self._client = client

    def export(self, batch: typing.Sequence[ReadableSpan]) -> SpanExportResult:
        status_code = self._client.send(batch)
        return SpanExportResult.SUCCESS if status_code == grpc.StatusCode.OK else SpanExportResult.FAILURE

    def force_flush(self, timeout_millis: int = 30000) -> ExporterFlushResult:
        """
        Nothing to flush.
        """
        return ExporterFlushResult.SUCCESS

    def shutdown(self) -> None:
        """
        Nothing to shut down.
        """
        pass
