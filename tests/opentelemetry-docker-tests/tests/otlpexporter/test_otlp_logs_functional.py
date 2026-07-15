# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import math
from collections.abc import Iterator

import pytest
from grpc import Compression as GRPCCompression
from inline_snapshot import snapshot

from opentelemetry._logs import Logger, SeverityNumber
from opentelemetry.exporter.http.transport._requests import (
    RequestsHTTPTransport,
)
from opentelemetry.exporter.http.transport._urllib3 import (
    Urllib3HTTPTransport,
)
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    OTLPLogExporter as GRPCLogExporter,
)
from opentelemetry.exporter.otlp.proto.http import (
    Compression as HTTPCompression,
)
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    OTLPLogExporter as HTTPLogExporter,
)
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import (
    LogRecordExporter,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.test._otlp_test_server import OtlpProtoTestServer

from . import CUSTOM_HEADERS, ExporterConfig, _attrs_to_dict

LOG_EXPORTER_CONFIGS: list[ExporterConfig[LogRecordExporter]] = [
    ExporterConfig(
        id="http-urllib3",
        exporter_class=HTTPLogExporter,
        kwargs={"endpoint": "http://localhost:4318/v1/logs"},
        lazy_kwargs={"_transport": Urllib3HTTPTransport},
    ),
    ExporterConfig(
        id="http-requests",
        exporter_class=HTTPLogExporter,
        kwargs={"endpoint": "http://localhost:4318/v1/logs"},
        lazy_kwargs={"_transport": RequestsHTTPTransport},
    ),
    ExporterConfig(
        id="http-urllib3-deflate",
        exporter_class=HTTPLogExporter,
        kwargs={
            "endpoint": "http://localhost:4318/v1/logs",
            "compression": HTTPCompression.Deflate,
        },
        lazy_kwargs={"_transport": Urllib3HTTPTransport},
    ),
    ExporterConfig(
        id="http-requests-deflate",
        exporter_class=HTTPLogExporter,
        kwargs={
            "endpoint": "http://localhost:4318/v1/logs",
            "compression": HTTPCompression.Deflate,
        },
        lazy_kwargs={"_transport": RequestsHTTPTransport},
    ),
    ExporterConfig(
        id="http-urllib3-gzip",
        exporter_class=HTTPLogExporter,
        kwargs={
            "endpoint": "http://localhost:4318/v1/logs",
            "compression": HTTPCompression.Gzip,
        },
        lazy_kwargs={"_transport": Urllib3HTTPTransport},
    ),
    ExporterConfig(
        id="http-requests-gzip",
        exporter_class=HTTPLogExporter,
        kwargs={
            "endpoint": "http://localhost:4318/v1/logs",
            "compression": HTTPCompression.Gzip,
        },
        lazy_kwargs={"_transport": RequestsHTTPTransport},
    ),
    ExporterConfig(
        id="http-urllib3-headers",
        exporter_class=HTTPLogExporter,
        kwargs={
            "endpoint": "http://localhost:4318/v1/logs",
            "headers": CUSTOM_HEADERS,
        },
        lazy_kwargs={"_transport": Urllib3HTTPTransport},
    ),
    ExporterConfig(
        id="http-requests-headers",
        exporter_class=HTTPLogExporter,
        kwargs={
            "endpoint": "http://localhost:4318/v1/logs",
            "headers": CUSTOM_HEADERS,
        },
        lazy_kwargs={"_transport": RequestsHTTPTransport},
    ),
    ExporterConfig(
        id="grpc",
        exporter_class=GRPCLogExporter,
        kwargs={"insecure": True},
    ),
    ExporterConfig(
        id="grpc-gzip",
        exporter_class=GRPCLogExporter,
        kwargs={"insecure": True, "compression": GRPCCompression.Gzip},
    ),
    ExporterConfig(
        id="grpc-headers",
        exporter_class=GRPCLogExporter,
        kwargs={"insecure": True, "headers": CUSTOM_HEADERS},
    ),
]


class TestLogsExporter:
    @pytest.fixture(
        scope="class", params=LOG_EXPORTER_CONFIGS, ids=lambda c: c.id
    )
    def config(self, request) -> ExporterConfig[LogRecordExporter]:
        return request.param

    @pytest.fixture(scope="class")
    def logger_provider(
        self,
        config: ExporterConfig[LogRecordExporter],
        server: OtlpProtoTestServer,
    ) -> Iterator[LoggerProvider]:
        provider = LoggerProvider(
            resource=Resource.create({"service.name": "test-service"}),
        )
        provider.add_log_record_processor(
            SimpleLogRecordProcessor(config.build())
        )
        try:
            yield provider
        finally:
            provider.shutdown()

    @pytest.fixture(scope="class")
    def logger(self, logger_provider: LoggerProvider) -> Logger:
        return logger_provider.get_logger(__name__)

    @pytest.fixture(autouse=True)
    def clear_server(self, server: OtlpProtoTestServer) -> None:
        server.clear()

    def test_log_body(self, logger: Logger, server: OtlpProtoTestServer):
        logger.emit(body="hello world", severity_number=SeverityNumber.INFO)

        recorded = server.get_log_record(timeout=5.0)
        assert recorded.log_record.body.string_value == snapshot("hello world")

    def test_log_severity_number(
        self, logger: Logger, server: OtlpProtoTestServer
    ):
        logger.emit(
            severity_number=SeverityNumber.ERROR, body="error occurred"
        )

        recorded = server.get_log_record(timeout=5.0)
        assert (
            recorded.log_record.severity_number == SeverityNumber.ERROR.value
        )

    def test_log_severity_text(
        self, logger: Logger, server: OtlpProtoTestServer
    ):
        logger.emit(
            severity_number=SeverityNumber.WARN,
            severity_text="WARN",
            body="warning",
        )

        recorded = server.get_log_record(timeout=5.0)
        assert recorded.log_record.severity_text == snapshot("WARN")

    def test_log_attributes(self, logger: Logger, server: OtlpProtoTestServer):
        logger.emit(
            body="attrs test",
            severity_number=SeverityNumber.INFO,
            attributes={
                "str_key": "hello",
                "int_key": 42,
                "float_key": 3.14,
                "bool_key": True,
            },
        )

        recorded = server.get_log_record(timeout=5.0)
        attrs = _attrs_to_dict(recorded.log_record.attributes)
        assert math.isclose(attrs.pop("float_key"), 3.14, abs_tol=1e-5)
        assert attrs == snapshot(
            {"str_key": "hello", "int_key": 42, "bool_key": True}
        )

    def test_scope_attributes(
        self, logger_provider: LoggerProvider, server: OtlpProtoTestServer
    ):
        logger = logger_provider.get_logger(
            "test.scope",
            version="1.0.0",
            attributes={"scope.key": "scope.val"},
        )
        logger.emit(body="scope test", severity_number=SeverityNumber.INFO)

        recorded = server.get_log_record(timeout=5.0)
        assert recorded.scope.name == snapshot("test.scope")
        assert recorded.scope.version == snapshot("1.0.0")
        assert _attrs_to_dict(recorded.scope.attributes) == snapshot(
            {"scope.key": "scope.val"}
        )

    def test_resource_attributes(
        self, logger: Logger, server: OtlpProtoTestServer
    ):
        logger.emit(body="resource test", severity_number=SeverityNumber.INFO)

        recorded = server.get_log_record(timeout=5.0)
        resource_attrs = _attrs_to_dict(recorded.resource.attributes)
        assert resource_attrs["service.name"] == snapshot("test-service")
