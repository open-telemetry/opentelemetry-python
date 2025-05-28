# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""OTLP Exporter"""

import threading
from abc import ABC, abstractmethod
from collections.abc import Sequence  # noqa: F401
from logging import getLogger
from os import environ
from time import sleep
from typing import (  # noqa: F401
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Literal,
    NewType,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from typing import Sequence as TypingSequence
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
from opentelemetry.exporter.otlp.proto.common._internal import (
    _create_exp_backoff_generator,
    _get_resource_data,
)
from opentelemetry.exporter.otlp.proto.grpc import (
    _OTLP_GRPC_HEADERS,
)
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
from opentelemetry.sdk._logs import LogData
from opentelemetry.sdk._logs.export import LogExportResult
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_INSECURE,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.sdk.metrics.export import MetricExportResult, MetricsData
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.util.re import parse_env_headers

logger = getLogger(__name__)
SDKDataT = TypeVar(
    "SDKDataT",
    TypingSequence[LogData],
    MetricsData,
    TypingSequence[ReadableSpan],
)
ResourceDataT = TypeVar("ResourceDataT")
TypingResourceT = TypeVar("TypingResourceT")
ExportServiceRequestT = TypeVar(
    "ExportServiceRequestT",
    ExportTraceServiceRequest,
    ExportMetricsServiceRequest,
    ExportLogsServiceRequest,
)
ExportResultT = TypeVar(
    "ExportResultT",
    LogExportResult,
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
            'Invalid value "{}" for compression envvar {}'.format(
                environ_value, environ_key
            )
        )


def environ_to_compression(environ_key: str) -> Optional[Compression]:
    environ_value = (
        environ[environ_key].lower().strip()
        if environ_key in environ
        else None
    )
    if (
        environ_value not in _ENVIRON_TO_COMPRESSION
        and environ_value is not None
    ):
        raise InvalidCompressionValueException(environ_key, environ_value)
    return _ENVIRON_TO_COMPRESSION[environ_value]


@deprecated(
    "Use one of the encoders from opentelemetry-exporter-otlp-proto-common instead. Deprecated since version 1.18.0.",
)
def get_resource_data(
    sdk_resource_scope_data: Dict[SDKResource, ResourceDataT],
    resource_class: Callable[..., TypingResourceT],
    name: str,
) -> List[TypingResourceT]:
    return _get_resource_data(sdk_resource_scope_data, resource_class, name)


def _read_file(file_path: str) -> Optional[bytes]:
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
    certificate_file: Optional[str],
    client_key_file: Optional[str],
    client_certificate_file: Optional[str],
) -> ChannelCredentials:
    root_certificates = (
        _read_file(certificate_file) if certificate_file else None
    )
    private_key = _read_file(client_key_file) if client_key_file else None
    certificate_chain = (
        _read_file(client_certificate_file)
        if client_certificate_file
        else None
    )

    return ssl_channel_credentials(
        root_certificates=root_certificates,
        private_key=private_key,
        certificate_chain=certificate_chain,
    )


def _get_credentials(
    creds: Optional[ChannelCredentials],
    certificate_file_env_key: str,
    client_key_file_env_key: str,
    client_certificate_file_env_key: str,
) -> ChannelCredentials:
    if creds is not None:
        return creds

    certificate_file = environ.get(certificate_file_env_key)
    if certificate_file:
        client_key_file = environ.get(client_key_file_env_key)
        client_certificate_file = environ.get(client_certificate_file_env_key)
        return _load_credentials(
            certificate_file, client_key_file, client_certificate_file
        )
    return ssl_channel_credentials()


# pylint: disable=no-member
class OTLPExporterMixin(
    ABC, Generic[SDKDataT, ExportServiceRequestT, ExportResultT, ExportStubT]
):
    """OTLP span exporter

    Args:
        endpoint: OpenTelemetry Collector receiver endpoint
        insecure: Connection type
        credentials: ChannelCredentials object for server authentication
        headers: Headers to send when exporting
        timeout: Backend request timeout in seconds
        compression: gRPC compression method to use
    """

    _MAX_RETRY_TIMEOUT = 64

    def __init__(
        self,
        stub: ExportStubT,
        result: ExportResultT,
        endpoint: Optional[str] = None,
        insecure: Optional[bool] = None,
        credentials: Optional[ChannelCredentials] = None,
        headers: Optional[
            Union[TypingSequence[Tuple[str, str]], Dict[str, str], str]
        ] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
    ):
        super().__init__()
        self._result = result
        self._stub = stub
        self._endpoint = endpoint or environ.get(
            OTEL_EXPORTER_OTLP_ENDPOINT, "http://localhost:4317"
        )

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

        self._headers = headers or environ.get(OTEL_EXPORTER_OTLP_HEADERS)
        if isinstance(self._headers, str):
            temp_headers = parse_env_headers(self._headers, liberal=True)
            self._headers = tuple(temp_headers.items())
        elif isinstance(self._headers, dict):
            self._headers = tuple(self._headers.items())
        if self._headers is None:
            self._headers = tuple(_OTLP_GRPC_HEADERS)
        else:
            self._headers = tuple(self._headers) + tuple(_OTLP_GRPC_HEADERS)

        self._timeout = timeout or int(
            environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, 10)
        )
        self._collector_kwargs = None

        compression = (
            environ_to_compression(OTEL_EXPORTER_OTLP_COMPRESSION)
            if compression is None
            else compression
        ) or Compression.NoCompression

        if insecure:
            self._channel = insecure_channel(
                self._endpoint, compression=compression
            )
        else:
            credentials = _get_credentials(
                credentials,
                OTEL_EXPORTER_OTLP_CERTIFICATE,
                OTEL_EXPORTER_OTLP_CLIENT_KEY,
                OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
            )
            self._channel = secure_channel(
                self._endpoint, credentials, compression=compression
            )
        self._client = self._stub(self._channel)  # type: ignore [reportCallIssue]

        self._export_lock = threading.Lock()
        self._shutdown = False

    @abstractmethod
    def _translate_data(
        self,
        data: SDKDataT,
    ) -> ExportServiceRequestT:
        pass

    def _export(
        self,
        data: SDKDataT,
    ) -> ExportResultT:
        # After the call to shutdown, subsequent calls to Export are
        # not allowed and should return a Failure result.
        if self._shutdown:
            logger.warning("Exporter already shutdown, ignoring batch")
            return self._result.FAILURE  # type: ignore [reportReturnType]

        # FIXME remove this check if the export type for traces
        # gets updated to a class that represents the proto
        # TracesData and use the code below instead.
        # logger.warning(
        #     "Transient error %s encountered while exporting %s, retrying in %ss.",
        #     error.code(),
        #     data.__class__.__name__,
        #     delay,
        # )
        # expo returns a generator that yields delay values which grow
        # exponentially. Once delay is greater than max_value, the yielded
        # value will remain constant.
        for delay in _create_exp_backoff_generator(
            max_value=self._MAX_RETRY_TIMEOUT
        ):
            if delay == self._MAX_RETRY_TIMEOUT or self._shutdown:
                return self._result.FAILURE  # type: ignore [reportReturnType]

            with self._export_lock:
                try:
                    self._client.Export(
                        request=self._translate_data(data),
                        metadata=self._headers,
                        timeout=self._timeout,
                    )

                    return self._result.SUCCESS  # type: ignore [reportReturnType]

                except RpcError as error:
                    code = error.code()  # type: ignore [reportAttributeAccessIssue]
                    if code in [
                        StatusCode.CANCELLED,
                        StatusCode.DEADLINE_EXCEEDED,
                        StatusCode.RESOURCE_EXHAUSTED,
                        StatusCode.ABORTED,
                        StatusCode.OUT_OF_RANGE,
                        StatusCode.UNAVAILABLE,
                        StatusCode.DATA_LOSS,
                    ]:
                        retry_info_bin = dict(error.trailing_metadata()).get(  # type: ignore [reportAttributeAccessIssue]
                            "google.rpc.retryinfo-bin"
                        )
                        if retry_info_bin is not None:
                            retry_info = RetryInfo()
                            retry_info.ParseFromString(retry_info_bin)
                            delay = (
                                retry_info.retry_delay.seconds
                                + retry_info.retry_delay.nanos / 1.0e9
                            )

                        logger.warning(
                            (
                                "Transient error %s encountered while exporting "
                                "%s to %s, retrying in %ss."
                            ),
                            code,
                            self._exporting,
                            self._endpoint,
                            delay,
                        )
                        sleep(delay)
                        continue
                    else:
                        logger.error(
                            "Failed to export %s to %s, error code: %s",
                            self._exporting,
                            self._endpoint,
                            code,
                            exc_info=code == StatusCode.UNKNOWN,
                        )

                    if code == StatusCode.OK:
                        return self._result.SUCCESS  # type: ignore [reportReturnType]

                    return self._result.FAILURE  # type: ignore [reportReturnType]

        return self._result.FAILURE  # type: ignore [reportReturnType]

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        if self._shutdown:
            logger.warning("Exporter already shutdown, ignoring call")
            return
        # wait for the last export if any
        self._export_lock.acquire(timeout=timeout_millis / 1e3)
        self._shutdown = True
        self._channel.close()
        self._export_lock.release()

    @property
    @abstractmethod
    def _exporting(self) -> str:
        """
        Returns a string that describes the overall exporter, to be used in
        warning messages.
        """
        pass
