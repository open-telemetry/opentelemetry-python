from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest as ProtoExportTraceServiceRequest,
    ExportTraceServiceResponse as ProtoExportTraceServiceResponse,
)
from opentelemetry.proto.trace.v1.trace_pb2 import (
    ResourceSpans as ProtoResourceSpans,
)

from opentelemetry._proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
    ExportTraceServiceResponse,
)
from opentelemetry._proto.trace.v1.trace_pb2 import ResourceSpans


def test_export_response_empty() -> None:
    assert ExportTraceServiceResponse().SerializeToString() == b""


def test_export_response_matches_proto() -> None:
    assert (
        ExportTraceServiceResponse().SerializeToString()
        == ProtoExportTraceServiceResponse().SerializeToString()
    )


def test_export_request_empty() -> None:
    assert ExportTraceServiceRequest().SerializeToString() == b""


def test_export_request_empty_matches_proto() -> None:
    assert (
        ExportTraceServiceRequest().SerializeToString()
        == ProtoExportTraceServiceRequest().SerializeToString()
    )


def test_export_request_with_empty_resource_spans() -> None:
    our = ExportTraceServiceRequest(resource_spans=[ResourceSpans()])
    proto = ProtoExportTraceServiceRequest(resource_spans=[ProtoResourceSpans()])
    assert our.SerializeToString() == proto.SerializeToString()


def test_export_request_with_schema_url() -> None:
    our = ExportTraceServiceRequest(
        resource_spans=[ResourceSpans(schema_url="https://example.com/schema")]
    )
    proto = ProtoExportTraceServiceRequest(
        resource_spans=[ProtoResourceSpans(schema_url="https://example.com/schema")]
    )
    assert our.SerializeToString() == proto.SerializeToString()


def test_export_request_multiple_resource_spans() -> None:
    our = ExportTraceServiceRequest(
        resource_spans=[
            ResourceSpans(schema_url="schema-a"),
            ResourceSpans(schema_url="schema-b"),
        ]
    )
    proto = ProtoExportTraceServiceRequest(
        resource_spans=[
            ProtoResourceSpans(schema_url="schema-a"),
            ProtoResourceSpans(schema_url="schema-b"),
        ]
    )
    assert our.SerializeToString() == proto.SerializeToString()
