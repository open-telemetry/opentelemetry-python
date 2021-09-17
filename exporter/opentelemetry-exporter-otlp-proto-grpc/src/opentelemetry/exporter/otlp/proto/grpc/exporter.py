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

import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
from os import environ
from time import sleep
from typing import Any, Callable, Dict, Generic, List, Optional
from typing import Sequence as TypingSequence
from typing import Text, TypeVar
from urllib.parse import urlparse

from backoff import expo
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
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.sdk.resources import Resource as SDKResource

logger = logging.getLogger(__name__)
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
        raise Exception(
            "Invalid type {} of value {}".format(type(value), value)
        )

    return any_value


def _translate_key_values(key: Text, value: Any) -> KeyValue:
    return KeyValue(key=key, value=_translate_value(value))


def get_resource_data(
    sdk_resource_instrumentation_library_data: Dict[
        SDKResource, ResourceDataT
    ],
    resource_class: Callable[..., TypingResourceT],
    name: str,
) -> List[TypingResourceT]:

    resource_data = []

    for (
        sdk_resource,
        instrumentation_library_data,
    ) in sdk_resource_instrumentation_library_data.items():

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
                    "instrumentation_library_{}".format(
                        name
                    ): instrumentation_library_data.values(),
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
        headers: Optional[Sequence] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
    ):
        super().__init__()

        endpoint = endpoint or environ.get(
            OTEL_EXPORTER_OTLP_ENDPOINT, "http://localhost:4317"
        )

        parsed_url = urlparse(endpoint)

        if insecure is None:
            if parsed_url.scheme == "https":
                insecure = False
            else:
                insecure = True

        if parsed_url.netloc:
            endpoint = parsed_url.netloc

        self._headers = headers or environ.get(OTEL_EXPORTER_OTLP_HEADERS)
        if isinstance(self._headers, str):
            temp_headers = []
            for header_pair in self._headers.split(","):
                key, value = header_pair.split("=", maxsplit=1)
                key = key.strip().lower()
                value = value.strip()
                temp_headers.append(
                    (
                        key,
                        value,
                    )
                )

            self._headers = tuple(temp_headers)

        self._timeout = timeout or int(
            environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, 10)
        )
        self._collector_span_kwargs = None

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

    def _export(self, data: TypingSequence[SDKDataT]) -> ExportResultT:

        max_value = 64
        # expo returns a generator that yields delay values which grow
        # exponentially. Once delay is greater than max_value, the yielded
        # value will remain constant.
        for delay in expo(max_value=max_value):

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

                    logger.debug(
                        "Waiting %ss before retrying export of span", delay
                    )
                    sleep(delay)
                    continue

                if error.code() == StatusCode.OK:
                    return self._result.SUCCESS

                return self._result.FAILURE

        return self._result.FAILURE

    def shutdown(self) -> None:
        pass
