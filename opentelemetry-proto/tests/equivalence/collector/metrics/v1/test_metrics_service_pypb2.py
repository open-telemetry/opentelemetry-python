from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest as ProtoExportMetricsServiceRequest,
    ExportMetricsServiceResponse as ProtoExportMetricsServiceResponse,
)
from opentelemetry.proto.metrics.v1.metrics_pb2 import (
    ResourceMetrics as ProtoResourceMetrics,
)

from opentelemetry._proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
    ExportMetricsServiceResponse,
)
from opentelemetry._proto.metrics.v1.metrics_pb2 import ResourceMetrics


def test_export_response_empty() -> None:
    assert ExportMetricsServiceResponse().SerializeToString() == b""


def test_export_response_matches_proto() -> None:
    assert (
        ExportMetricsServiceResponse().SerializeToString()
        == ProtoExportMetricsServiceResponse().SerializeToString()
    )


def test_export_request_empty() -> None:
    assert ExportMetricsServiceRequest().SerializeToString() == b""


def test_export_request_empty_matches_proto() -> None:
    assert (
        ExportMetricsServiceRequest().SerializeToString()
        == ProtoExportMetricsServiceRequest().SerializeToString()
    )


def test_export_request_with_empty_resource_metrics() -> None:
    our = ExportMetricsServiceRequest(resource_metrics=[ResourceMetrics()])
    proto = ProtoExportMetricsServiceRequest(resource_metrics=[ProtoResourceMetrics()])
    assert our.SerializeToString() == proto.SerializeToString()


def test_export_request_with_schema_url() -> None:
    our = ExportMetricsServiceRequest(
        resource_metrics=[ResourceMetrics(schema_url="https://example.com/schema")]
    )
    proto = ProtoExportMetricsServiceRequest(
        resource_metrics=[ProtoResourceMetrics(schema_url="https://example.com/schema")]
    )
    assert our.SerializeToString() == proto.SerializeToString()


def test_export_request_multiple_resource_metrics() -> None:
    our = ExportMetricsServiceRequest(
        resource_metrics=[
            ResourceMetrics(schema_url="schema-a"),
            ResourceMetrics(schema_url="schema-b"),
        ]
    )
    proto = ProtoExportMetricsServiceRequest(
        resource_metrics=[
            ProtoResourceMetrics(schema_url="schema-a"),
            ProtoResourceMetrics(schema_url="schema-b"),
        ]
    )
    assert our.SerializeToString() == proto.SerializeToString()
