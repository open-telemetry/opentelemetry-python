# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import os
import random
import threading
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from collections.abc import Sequence as TypingSequence
from logging import getLogger
from os import environ
from time import time
from typing import Generic, Literal, TypeVar
from urllib.parse import urlparse

from opentelemetry.exporter.otlp._proto.grpc._pygrpc.api import (
    ChannelCredentials,
    Compression,
    RpcError,
    StatusCode,
    insecure_channel,
    secure_channel,
    ssl_channel_credentials,
)

from opentelemetry.exporter.otlp._proto.common._exporter_metrics import (
    create_exporter_metrics,
)
from opentelemetry.exporter.otlp._proto.grpc import (
    _OTLP_GRPC_CHANNEL_OPTIONS,
)
from opentelemetry.metrics import MeterProvider
from opentelemetry._proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
)
from opentelemetry._proto.collector.logs.v1.logs_service_pb2_grpc import (
    LogsServiceStub,
)
from opentelemetry._proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry._proto.collector.metrics.v1.metrics_service_pb2_grpc import (
    MetricsServiceStub,
)
from opentelemetry._proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry._proto.collector.trace.v1.trace_service_pb2_grpc import (
    TraceServiceStub,
)
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

_RETRYABLE_ERROR_CODES = frozenset([
    StatusCode.CANCELLED,
    StatusCode.DEADLINE_EXCEEDED,
    StatusCode.RESOURCE_EXHAUSTED,
    StatusCode.ABORTED,
    StatusCode.OUT_OF_RANGE,
    StatusCode.UNAVAILABLE,
    StatusCode.DATA_LOSS,
])
_MAX_RETRYS = 6
logger = getLogger(__name__)
logger.addFilter(DuplicateFilter())

SDKDataT = TypeVar(
    "SDKDataT",
    TypingSequence[ReadableLogRecord],
    MetricsData,
    TypingSequence[ReadableSpan],
)
ExportServiceRequestT = TypeVar(
    "ExportServiceRequestT",
    ExportTraceServiceRequest,
    ExportMetricsServiceRequest,
    ExportLogsServiceRequest,
)
ExportResultT = TypeVar(
    "ExportResultT",
    LogRecordExportResult,
    MetricExportResult,
    SpanExportResult,
)
ExportStubT = TypeVar(
    "ExportStubT", TraceServiceStub, MetricsServiceStub, LogsServiceStub
)

_ENVIRON_TO_COMPRESSION = {
    None: None,
    "gzip": Compression.Gzip,
}


class InvalidCompressionValueException(Exception):
    def __init__(self, environ_key: str, environ_value: str):
        super().__init__(
            f'Invalid value "{environ_value}" for compression envvar {environ_key}'
        )


def environ_to_compression(environ_key: str) -> Compression | None:
    environ_value = (
        environ[environ_key].lower().strip()
        if environ_key in environ
        else None
    )
    if environ_value not in _ENVIRON_TO_COMPRESSION and environ_value is not None:
        raise InvalidCompressionValueException(environ_key, environ_value)
    return _ENVIRON_TO_COMPRESSION[environ_value]


def _read_file(file_path: str) -> bytes | None:
    try:
        with open(file_path, "rb") as file:
            return file.read()
    except FileNotFoundError as e:
        logger.exception(
            "Failed to read file: %s. Please check if the file exists and is accessible.",
            e.filename,
        )
        return None


def _load_credentials(
    certificate_file: str | None,
    client_key_file: str | None,
    client_certificate_file: str | None,
) -> ChannelCredentials:
    root_certificates = _read_file(certificate_file) if certificate_file else None
    private_key = _read_file(client_key_file) if client_key_file else None
    certificate_chain = _read_file(client_certificate_file) if client_certificate_file else None
    return ssl_channel_credentials(
        root_certificates=root_certificates,
        private_key=private_key,
        certificate_chain=certificate_chain,
    )


def _get_credentials(
    creds: ChannelCredentials | None,
    credential_entry_point_env_key: str,
    certificate_file_env_key: str,
    client_key_file_env_key: str,
    client_certificate_file_env_key: str,
) -> ChannelCredentials:
    if creds is not None:
        return creds
    _credential_env = environ.get(credential_entry_point_env_key)
    if _credential_env:
        try:
            maybe_channel_creds = next(
                iter(
                    entry_points(
                        group="opentelemetry_otlp_credential_provider",
                        name=_credential_env,
                    )
                )
            ).load()()
        except StopIteration:
            raise RuntimeError(
                f"Requested component '{_credential_env}' not found in "
                f"entry point 'opentelemetry_otlp_credential_provider'"
            )
        if isinstance(maybe_channel_creds, ChannelCredentials):
            return maybe_channel_creds
        else:
            raise RuntimeError(
                f"Requested component '{_credential_env}' is of type {type(maybe_channel_creds)}"
                f" must be of type `grpc.ChannelCredentials`."
            )

    certificate_file = environ.get(certificate_file_env_key)
    if certificate_file:
        client_key_file = environ.get(client_key_file_env_key)
        client_certificate_file = environ.get(client_certificate_file_env_key)
        credentials = _load_credentials(certificate_file, client_key_file, client_certificate_file)
        if credentials is not None:
            return credentials
    return ssl_channel_credentials()


class OTLPExporterMixin(ABC, Generic[SDKDataT, ExportServiceRequestT, ExportResultT, ExportStubT]):
    def __init__(
        self,
        stub: ExportStubT,
        result: ExportResultT,
        endpoint: str | None = None,
        insecure: bool | None = None,
        credentials: ChannelCredentials | None = None,
        headers: TypingSequence[tuple[str, str]] | dict[str, str] | str | None = None,
        timeout: float | None = None,
        compression: Compression | None = None,
        channel_options: tuple[tuple[str, str]] | None = None,
        retryable_error_codes: Iterable[StatusCode] | None = None,
        *,
        component_type: OtelComponentTypeValues | None = None,
        signal: Literal["traces", "metrics", "logs"] = "traces",
        meter_provider: MeterProvider | None = None,
    ):
        super().__init__()
        self._result = result
        self._stub = stub
        self._endpoint = endpoint or environ.get(OTEL_EXPORTER_OTLP_ENDPOINT, "http://localhost:4317")

        parsed_url = urlparse(self._endpoint)

        if parsed_url.scheme == "https":
            insecure = False
        insecure_exporter = environ.get(OTEL_EXPORTER_OTLP_INSECURE)
        if insecure is None:
            if insecure_exporter is not None:
                insecure = insecure_exporter.lower() == "true"
            else:
                insecure = parsed_url.scheme == "http"

        if parsed_url.netloc:
            self._endpoint = parsed_url.netloc

        self._insecure = insecure
        self._credentials = credentials
        self._headers = headers or environ.get(OTEL_EXPORTER_OTLP_HEADERS)
        if isinstance(self._headers, str):
            temp_headers = parse_env_headers(self._headers, liberal=True)
            self._headers = tuple(temp_headers.items())
        elif isinstance(self._headers, dict):
            self._headers = tuple(self._headers.items())
        if self._headers is None:
            self._headers = tuple()

        if channel_options:
            overridden_options = {opt_name for (opt_name, _) in channel_options}
            default_options = tuple(
                (opt_name, opt_value)
                for opt_name, opt_value in _OTLP_GRPC_CHANNEL_OPTIONS
                if opt_name not in overridden_options
            )
            self._channel_options = default_options + channel_options
        else:
            self._channel_options = tuple(_OTLP_GRPC_CHANNEL_OPTIONS)

        self._timeout = timeout or float(environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, 10))
        self._collector_kwargs = None

        self._compression = (
            environ_to_compression(OTEL_EXPORTER_OTLP_COMPRESSION)
            if compression is None
            else compression
        ) or Compression.NoCompression

        self._retryable_error_codes = retryable_error_codes or os.environ.get(
            _OTEL_PYTHON_EXPORTER_OTLP_GRPC_RETRYABLE_ERROR_CODES
        )
        if isinstance(self._retryable_error_codes, str):
            self._retryable_error_codes = frozenset(
                StatusCode[code.strip().upper()]
                for code in self._retryable_error_codes.split(",")
                if code.strip()
            )
        elif self._retryable_error_codes is not None:
            self._retryable_error_codes = frozenset(self._retryable_error_codes)
        else:
            self._retryable_error_codes = _RETRYABLE_ERROR_CODES

        self._channel = None
        self._client = None
        self._shutdown_in_progress = threading.Event()
        self._shutdown = False

        if not self._insecure:
            self._credentials = _get_credentials(
                self._credentials,
                _OTEL_PYTHON_EXPORTER_OTLP_GRPC_CREDENTIAL_PROVIDER,
                OTEL_EXPORTER_OTLP_CERTIFICATE,
                OTEL_EXPORTER_OTLP_CLIENT_KEY,
                OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
            )

        self._component_type = component_type
        self._signal: Literal["traces", "metrics", "logs"] = signal
        self._parsed_url = parsed_url
        self._metrics = create_exporter_metrics(
            self._component_type,
            signal,
            parsed_url,
            meter_provider,
            os.environ.get(OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED, "")
            .strip()
            .lower()
            == "true",
        )

        self._initialize_channel_and_stub()

    def _initialize_channel_and_stub(self):
        if self._insecure:
            self._channel = insecure_channel(
                self._endpoint,
                compression=self._compression,
                options=self._channel_options,
            )
        else:
            assert self._credentials is not None
            self._channel = secure_channel(
                self._endpoint,
                self._credentials,
                compression=self._compression,
                options=self._channel_options,
            )
        self._client = self._stub(self._channel)

    @abstractmethod
    def _translate_data(self, data: SDKDataT) -> ExportServiceRequestT:
        pass

    @abstractmethod
    def _count_data(self, data: SDKDataT) -> int:
        pass

    def _export(self, data: SDKDataT) -> ExportResultT:
        if self._shutdown:
            logger.warning("Exporter already shutdown, ignoring batch")
            return self._result.FAILURE

        with self._metrics.export_operation(self._count_data(data)) as result:
            deadline_sec = time() + self._timeout
            for retry_num in range(_MAX_RETRYS):
                backoff_seconds = 2**retry_num * random.uniform(0.8, 1.2)
                try:
                    if self._client is None:
                        return self._result.FAILURE
                    self._client.Export(
                        request=self._translate_data(data),
                        metadata=self._headers,
                        timeout=deadline_sec - time(),
                    )
                    return self._result.SUCCESS
                except RpcError as error:
                    if (
                        error.code() == StatusCode.UNAVAILABLE
                        and retry_num == 0
                    ):
                        logger.debug(
                            "Reinitializing gRPC channel for %s exporter due to UNAVAILABLE error",
                            self._exporting,
                        )
                        try:
                            if self._channel:
                                self._channel.close()
                        except Exception as e:
                            logger.debug(
                                "Error closing channel for %s exporter to %s: %s",
                                self._exporting,
                                self._endpoint,
                                str(e),
                            )
                        self._initialize_channel_and_stub()

                    if (
                        error.code() not in self._retryable_error_codes
                        or retry_num + 1 == _MAX_RETRYS
                        or backoff_seconds > (deadline_sec - time())
                        or self._shutdown
                    ):
                        logger.error(
                            "Failed to export %s to %s, error code: %s, error details: %s",
                            self._exporting,
                            self._endpoint,
                            error.code(),
                            error.details(),
                            exc_info=error.code() == StatusCode.UNKNOWN,
                        )
                        result.error = error
                        result.error_attrs = {RPC_RESPONSE_STATUS_CODE: error.code().name}
                        return self._result.FAILURE
                    logger.warning(
                        "Transient error %s encountered while exporting %s to %s, retrying in %.2fs. Error details: %s",
                        error.code(),
                        self._exporting,
                        self._endpoint,
                        backoff_seconds,
                        error.details(),
                    )
                shutdown = self._shutdown_in_progress.wait(backoff_seconds)
                if shutdown:
                    logger.warning("Shutdown in progress, aborting retry.")
                    break
            return self._result.FAILURE

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        if self._shutdown:
            logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._shutdown_in_progress.set()
        if self._channel:
            self._channel.close()

    @property
    @abstractmethod
    def _exporting(self) -> str:
        pass

    def _set_meter_provider(self, meter_provider: MeterProvider) -> None:
        self._metrics = create_exporter_metrics(
            self._component_type,
            self._signal,
            self._parsed_url,
            meter_provider,
            os.environ.get(OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED, "")
            .strip()
            .lower()
            == "true",
        )
