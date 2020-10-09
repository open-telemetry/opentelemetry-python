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
from collections.abc import Mapping, Sequence
from time import sleep
from typing import Any, Callable, Dict, Generic, List, Optional
from typing import Sequence as TypingSequence
from typing import Text, Tuple, TypeVar

from backoff import expo
from google.rpc.error_details_pb2 import RetryInfo
from grpc import (
    ChannelCredentials,
    RpcError,
    StatusCode,
    insecure_channel,
    secure_channel,
)

from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry.proto.resource.v1.resource_pb2 import Resource
from opentelemetry.sdk.resources import Resource as SDKResource

logger = logging.getLogger(__name__)
SDKDataT = TypeVar("SDKDataT")
ResourceDataT = TypeVar("ResourceDataT")
TypingResourceT = TypeVar("TypingResourceT")
ExportServiceRequestT = TypeVar("ExportServiceRequestT")
ExportResultT = TypeVar("ExportResultT")


def _translate_key_values(key: Text, value: Any) -> KeyValue:

    if isinstance(value, bool):
        any_value = AnyValue(bool_value=value)

    elif isinstance(value, str):
        any_value = AnyValue(string_value=value)

    elif isinstance(value, int):
        any_value = AnyValue(int_value=value)

    elif isinstance(value, float):
        any_value = AnyValue(double_value=value)

    elif isinstance(value, Sequence):
        any_value = AnyValue(array_value=value)

    elif isinstance(value, Mapping):
        any_value = AnyValue(kvlist_value=value)

    else:
        raise Exception(
            "Invalid type {} of value {}".format(type(value), value)
        )

    return KeyValue(key=key, value=any_value)


def _get_resource_data(
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
                    "instrumentation_library_{}".format(name): [
                        instrumentation_library_data
                    ],
                }
            )
        )

    return resource_data


# pylint: disable=no-member
class OTLPExporterMixin(
    ABC, Generic[SDKDataT, ExportServiceRequestT, ExportResultT]
):
    """OTLP span/metric exporter

    Args:
        endpoint: OpenTelemetry Collector receiver endpoint
        credentials: ChannelCredentials object for server authentication
        metadata: Metadata to send when exporting
    """

    def __init__(
        self,
        endpoint: str = "localhost:55680",
        credentials: ChannelCredentials = None,
        metadata: Optional[Tuple[Any]] = None,
    ):
        super().__init__()

        self._metadata = metadata
        self._collector_span_kwargs = None

        if credentials is None:
            self._client = self._stub(insecure_channel(endpoint))
        else:
            self._client = self._stub(secure_channel(endpoint, credentials))

    @abstractmethod
    def _translate_data(
        self, data: TypingSequence[SDKDataT]
    ) -> ExportServiceRequestT:
        pass

    def _export(self, data: TypingSequence[SDKDataT]) -> ExportResultT:
        # expo returns a generator that yields delay values which grow
        # exponentially. Once delay is greater than max_value, the yielded
        # value will remain constant.
        # max_value is set to 900 (900 seconds is 15 minutes) to use the same
        # value as used in the Go implementation.

        max_value = 900

        for delay in expo(max_value=max_value):

            if delay == max_value:
                return self._result.FAILURE

            try:
                self._client.Export(
                    request=self._translate_data(data),
                    metadata=self._metadata,
                )

                return self._result.SUCCESS

            except RpcError as error:

                if error.code() in [
                    StatusCode.CANCELLED,
                    StatusCode.DEADLINE_EXCEEDED,
                    StatusCode.PERMISSION_DENIED,
                    StatusCode.UNAUTHENTICATED,
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
