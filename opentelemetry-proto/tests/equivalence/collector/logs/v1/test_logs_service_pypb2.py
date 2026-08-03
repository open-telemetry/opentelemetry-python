from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest as ProtoExportLogsServiceRequest,
    ExportLogsServiceResponse as ProtoExportLogsServiceResponse,
)
from opentelemetry.proto.logs.v1.logs_pb2 import (
    ResourceLogs as ProtoResourceLogs,
)

from opentelemetry._proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
    ExportLogsServiceResponse,
)
from opentelemetry._proto.logs.v1.logs_pb2 import ResourceLogs


def test_export_response_empty() -> None:
    assert ExportLogsServiceResponse().SerializeToString() == b""


def test_export_response_matches_proto() -> None:
    assert (
        ExportLogsServiceResponse().SerializeToString()
        == ProtoExportLogsServiceResponse().SerializeToString()
    )


def test_export_request_empty() -> None:
    assert ExportLogsServiceRequest().SerializeToString() == b""


def test_export_request_empty_matches_proto() -> None:
    assert (
        ExportLogsServiceRequest().SerializeToString()
        == ProtoExportLogsServiceRequest().SerializeToString()
    )


def test_export_request_with_empty_resource_logs() -> None:
    our = ExportLogsServiceRequest(resource_logs=[ResourceLogs()])
    proto = ProtoExportLogsServiceRequest(resource_logs=[ProtoResourceLogs()])
    assert our.SerializeToString() == proto.SerializeToString()


def test_export_request_with_schema_url() -> None:
    our = ExportLogsServiceRequest(
        resource_logs=[ResourceLogs(schema_url="https://example.com/schema")]
    )
    proto = ProtoExportLogsServiceRequest(
        resource_logs=[ProtoResourceLogs(schema_url="https://example.com/schema")]
    )
    assert our.SerializeToString() == proto.SerializeToString()


def test_export_request_multiple_resource_logs() -> None:
    our = ExportLogsServiceRequest(
        resource_logs=[
            ResourceLogs(schema_url="schema-a"),
            ResourceLogs(schema_url="schema-b"),
        ]
    )
    proto = ProtoExportLogsServiceRequest(
        resource_logs=[
            ProtoResourceLogs(schema_url="schema-a"),
            ProtoResourceLogs(schema_url="schema-b"),
        ]
    )
    assert our.SerializeToString() == proto.SerializeToString()
