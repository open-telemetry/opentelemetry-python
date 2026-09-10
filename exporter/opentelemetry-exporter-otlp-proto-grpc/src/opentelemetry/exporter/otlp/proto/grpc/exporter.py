# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""OTLP Exporter

This module provides a mixin class for OTLP exporters that send telemetry data
to an OTLP-compatible receiver via gRPC. It includes a configurable reconnection
logic to handle transient collector outages.

"""

import os
import random
import threading
from abc import ABC, abstractmethod
from collections.abc import (
    Callable,
    Iterable,
    Sequence,  # noqa: F401
)
from collections.abc import Sequence as TypingSequence
from logging import getLogger
from os import environ
from time import time
from typing import (  # noqa: F401
    Any,
    Generic,
    Literal,
    NewType,
    Optional,
    TypeVar,
)
from urllib.parse import urlparse

from google.rpc.error_details_pb2 import RetryInfo
from typing_extensions import deprecated

from grpc import (
    ChannelCredentials,
    Compression,
    RpcError,
    StatusCode,
    insecure_channel,
    secure_channel,
    ssl_channel_credentials,
)
from opentelemetry.exporter.otlp.proto.common._exporter_metrics import (
    create_exporter_metrics,
)
from opentelemetry.exporter.otlp.proto.common._internal import (
    _get_resource_data,
)
from opentelemetry.exporter.otlp.proto.grpc import (
    _OTLP_GRPC_CHANNEL_OPTIONS,
)
from opentelemetry.metrics import MeterProvider
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
)
from opentelemetry.proto.collector.logs.v1.logs_service_pb2_grpc import (
    LogsServiceStub,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2_grpc import (
    MetricsServiceStub,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc import (
    TraceServiceStub,
)
from opentelemetry.proto.common.v1.common_pb2 import (  # noqa: F401
    AnyValue,
    ArrayValue,
    KeyValue,
)
from opentelemetry.proto.resource.v1.resource_pb2 import Resource  # noqa: F401
from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.sdk._logs.export import LogRecordExportResult
from opentelemetry.sdk._shared_internal import DuplicateFilter
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_GRPC_CREDENTIAL_PROVIDER,
    _OTEL_PYTHON_EXPORTER_OTLP_GRPC_RETRYABLE_ERROR_CODES,
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_INSECURE,
    OTEL_EXPORTER_OTLP_TIMEOUT,
    OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED,
)
from opentelemetry.sdk.metrics.export import MetricExportResult, MetricsData
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)
from opentelemetry.semconv._incubating.attributes.rpc_attributes import (
    RPC_RESPONSE_STATUS_CODE,
)
from opentelemetry.util._importlib_metadata import entry_points
from opentelemetry.util.re import parse_env_headers

_RETRYABLE_ERROR_CODES = frozenset(
    [
        StatusCode.CANCELLED,
        StatusCode.DEADLINE_EXCEEDED,
        StatusCode.RESOURCE_EXHAUSTED,
        StatusCode.ABORTED,
        StatusCode.OUT_OF_RANGE,
        StatusCode.UNAVAILABLE,
        StatusCode.DATA_LOSS,
    ]
)
_MAX_RETRYS = 6
logger = getLogger(__name__)
# This prevents logs generated when a log fails to be written to generate another log which fails to be written etc. etc.
logger.addFilter(DuplicateFilter())

SDKDataT = TypeVar(
    "SDKDataT",
    bound=object,
)

OTLPExporterMixin: type = type


class OTLPExporterMixin(Generic[SDKDataT], ABC):
    """Mixin class for OTLP exporters that send telemetry data to an OTLP-compatible receiver via gRPC.

    Includes a configurable reconnection logic to handle transient collector outages.

    """

    def __init__(
        self,
        endpoint: str,
        scheme: str = "http",
        timeout: int = 10,
        **kwargs: Any,
    ) -> None:
        self._endpoint = endpoint
        self._scheme = scheme
        self._timeout = timeout
        self._reconnect_timeout = 60.0
        self._max_retrys = _MAX_RETRYS
        self._otel_metrics_enabled = environ.get(
            OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED, "true"
        )
        self._logger = logger
        super().__init__(**kwargs)

    def _get_channel_credentials(
        self,
        insecure: bool = False,
        credentials: ChannelCredentials | None = None,
    ) -> ChannelCredentials:
        """Create channel credentials based on configuration."""
        if insecure and credentials is None:
            return insecure_channel()
        if not insecure and credentials is not None:
            return credentials
        return ssl_channel_credentials()

    def _get_stub(
        self,
        service: type,
        prefix: str | None = None,
    ) -> type:
        """Create a stub for the specific service."""
        stub = service(self._endpoint, channel=self._channel)
        if prefix is not None:
            return prefix
        return stub

    def __aenter__(self) -> "OTLPExporterMixin[SDKDataT]":
        """Async context manager entry."""
        return self

    def __aexit__(
        self,
        exc_type: type | None = None,
        exc_val: Any | None = None,
        exc_tb: Any | None = None,
    ) -> None | bool:
        """Async context manager exit."""
        return None

    def __iter__(self) -> Iterable[SDKDataT]:
        """Return iterator over data."""
        return self

    def __len__(self) -> int:
        """Return length of data."""
        return 0

    def __reversed__(self) -> Iterable[SDKDataT]:
        """Return reversed data."""
        return self

    def _get_resource(self, sdk_resource: SDKResource | None = None) -> SDKResource:
        """Get the resource associated with this exporter."""
        if sdk_resource is not None:
            return sdk_resource
        return Resource.create()

    @abstractmethod
    def _get_data_type(
        self,
        data: SDKDataT,
    ) -> type:
        """Get the data type for this exporter's data."""
        pass