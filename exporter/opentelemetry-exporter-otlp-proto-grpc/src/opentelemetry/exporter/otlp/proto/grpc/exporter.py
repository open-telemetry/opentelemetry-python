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

from logging import getLogger
from abc import ABC, abstractmethod
from collections.abc import Sequence
from os import environ
from time import sleep
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, Union
from typing import Sequence as TypingSequence
from typing import TypeVar
from urllib.parse import urlparse
from opentelemetry.sdk.trace import ReadableSpan

import backoff
from google.rpc.error_details_pb2 import RetryInfo
from grpc import (
    ChannelCredentials,
    Compression,
    RpcError,
    StatusCode,
    insecure_channel,
    secure_channel,
    ssl_channel_credentials,
)

from opentelemetry.proto.common.v1.common_pb2 import (
    AnyValue,
    ArrayValue,
    KeyValue,
)
from opentelemetry.proto.resource.v1.resource_pb2 import Resource
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_INSECURE,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.sdk.metrics.export import MetricsData
from opentelemetry.util.re import parse_env_headers
from opentelemetry.exporter.otlp.proto.grpc import (
    _OTLP_GRPC_HEADERS,
)

logger = getLogger(__name__)
SDKDataT = TypeVar("SDKDataT")
ResourceDataT = TypeVar("ResourceDataT")
TypingResourceT = TypeVar("TypingResourceT")
ExportServiceRequestT = TypeVar("ExportServiceRequestT")
ExportResultT = TypeVar("ExportResultT")

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
    if environ_value not in _ENVIRON_TO_COMPRESSION:
        raise InvalidCompressionValueException(environ_key, environ_value)
    return _ENVIRON_TO_COMPRESSION[environ_value]


def _translate_value(value: Any) -> KeyValue:

    if isinstance(value, bool):
        any_value = AnyValue(bool_value=value)

    elif isinstance(value, str):
        any_value = AnyValue(string_value=value)

    elif isinstance(value, int):
        any_value = AnyValue(int_value=value)

    elif isinstance(value, float):
        any_value = AnyValue(double_value=value)

    elif isinstance(value, Sequence):
        any_value = AnyValue(
            array_value=ArrayValue(values=[_translate_value(v) for v in value])
        )

    # Tracing specs currently does not support Mapping type attributes
    # elif isinstance(value, Mapping):
    #     any_value = AnyValue(
    #         kvlist_value=KeyValueList(
    #             values=[
    #                 _translate_key_values(str(k), v) for k, v in value.items()
    #             ]
    #         )
    #     )

    else:
        raise Exception(f"Invalid type {type(value)} of value {value}")

    return any_value


def _translate_key_values(key: str, value: Any) -> KeyValue:
    return KeyValue(key=key, value=_translate_value(value))


def get_resource_data(
    sdk_resource_scope_data: Dict[SDKResource, ResourceDataT],
    resource_class: Callable[..., TypingResourceT],
    name: str,
) -> List[TypingResourceT]:

    resource_data = []

    for (
        sdk_resource,
        scope_data,
    ) in sdk_resource_scope_data.items():

        collector_resource = Resource()

        for key, value in sdk_resource.attributes.items():

            try:
                # pylint: disable=no-member
                collector_resource.attributes.append(
                    _translate_key_values(key, value)
                )
            except Exception as error:  # pylint: disable=broad-except
                logger.exception(error)

        resource_data.append(
            resource_class(
                **{
                    "resource": collector_resource,
                    "scope_{}".format(name): scope_data.values(),
                }
            )
        )

    return resource_data


def _load_credential_from_file(filepath) -> ChannelCredentials:
    try:
        with open(filepath, "rb") as creds_file:
            credential = creds_file.read()
            return ssl_channel_credentials(credential)
    except FileNotFoundError:
        logger.exception("Failed to read credential file")
        return None


def _get_credentials(creds, environ_key):
    if creds is not None:
        return creds
    creds_env = environ.get(environ_key)
    if creds_env:
        return _load_credential_from_file(creds_env)
    return ssl_channel_credentials()


# Work around API change between backoff 1.x and 2.x. Since 2.0.0 the backoff
# wait generator API requires a first .send(None) before reading the backoff
# values from the generator.
_is_backoff_v2 = next(backoff.expo()) is None


def _expo(*args, **kwargs):
    gen = backoff.expo(*args, **kwargs)
    if _is_backoff_v2:
        gen.send(None)
    return gen


# pylint: disable=no-member
class OTLPExporterMixin(
    ABC, Generic[SDKDataT, ExportServiceRequestT, ExportResultT]
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

    def __init__(
        self,
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

        endpoint = endpoint or environ.get(
            OTEL_EXPORTER_OTLP_ENDPOINT, "http://localhost:4317"
        )

        parsed_url = urlparse(endpoint)

        if parsed_url.scheme == "https":
            insecure = False
        if insecure is None:
            insecure = environ.get(OTEL_EXPORTER_OTLP_INSECURE)
            if insecure is not None:
                insecure = insecure.lower() == "true"
            else:
                if parsed_url.scheme == "http":
                    insecure = True
                else:
                    insecure = False

        if parsed_url.netloc:
            endpoint = parsed_url.netloc

        self._headers = headers or environ.get(OTEL_EXPORTER_OTLP_HEADERS)
        if isinstance(self._headers, str):
            temp_headers = parse_env_headers(self._headers)
            self._headers = tuple(temp_headers.items())
        elif isinstance(self._headers, dict):
            self._headers = tuple(self._headers.items())
        if self._headers is None:
            self._headers = tuple(_OTLP_GRPC_HEADERS)
        else:
            self._headers = self._headers + tuple(_OTLP_GRPC_HEADERS)

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
            self._client = self._stub(
                insecure_channel(endpoint, compression=compression)
            )
        else:
            credentials = _get_credentials(
                credentials, OTEL_EXPORTER_OTLP_CERTIFICATE
            )
            self._client = self._stub(
                secure_channel(endpoint, credentials, compression=compression)
            )

    @abstractmethod
    def _translate_data(
        self, data: TypingSequence[SDKDataT]
    ) -> ExportServiceRequestT:
        pass

    def _translate_attributes(self, attributes) -> TypingSequence[KeyValue]:
        output = []
        if attributes:

            for key, value in attributes.items():
                try:
                    output.append(_translate_key_values(key, value))
                except Exception as error:  # pylint: disable=broad-except
                    logger.exception(error)
        return output

    def _export(
        self, data: Union[TypingSequence[ReadableSpan], MetricsData]
    ) -> ExportResultT:

        # FIXME remove this check if the export type for traces
        # gets updated to a class that represents the proto
        # TracesData and use the code below instead.
        # logger.warning(
        #     "Transient error %s encountered while exporting %s, retrying in %ss.",
        #     error.code(),
        #     data.__class__.__name__,
        #     delay,
        # )
        max_value = 64
        # expo returns a generator that yields delay values which grow
        # exponentially. Once delay is greater than max_value, the yielded
        # value will remain constant.
        for delay in _expo(max_value=max_value):

            if delay == max_value:
                return self._result.FAILURE

            try:
                self._client.Export(
                    request=self._translate_data(data),
                    metadata=self._headers,
                    timeout=self._timeout,
                )

                return self._result.SUCCESS

            except RpcError as error:

                if error.code() in [
                    StatusCode.CANCELLED,
                    StatusCode.DEADLINE_EXCEEDED,
                    StatusCode.RESOURCE_EXHAUSTED,
                    StatusCode.ABORTED,
                    StatusCode.OUT_OF_RANGE,
                    StatusCode.UNAVAILABLE,
                    StatusCode.DATA_LOSS,
                ]:

                    retry_info_bin = dict(error.trailing_metadata()).get(
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
                            "%s, retrying in %ss."
                        ),
                        error.code(),
                        self._exporting,
                        delay,
                    )
                    sleep(delay)
                    continue
                else:
                    logger.error(
                        "Failed to export %s, error code: %s",
                        self._exporting,
                        error.code(),
                    )

                if error.code() == StatusCode.OK:
                    return self._result.SUCCESS

                return self._result.FAILURE

        return self._result.FAILURE

    def shutdown(self) -> None:
        pass

    @property
    @abstractmethod
    def _exporting(self) -> str:
        """
        Returns a string that describes the overall exporter, to be used in
        warning messages.
        """
        pass
