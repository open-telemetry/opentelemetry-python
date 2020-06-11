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

"""OTLP Span Exporter"""

import logging
from abc import ABC, abstractmethod
from time import sleep

from backoff import expo
from google.rpc.error_details_pb2 import RetryInfo
from grpc import (
    ChannelCredentials,
    RpcError,
    StatusCode,
    insecure_channel,
    secure_channel,
)

logger = logging.getLogger(__name__)


def translate_key_values(key, value):
    key_value = {"key": key}

    if isinstance(value, bool):
        key_value["bool_value"] = value

    elif isinstance(value, str):
        key_value["string_value"] = value

    elif isinstance(value, int):
        key_value["int_value"] = value

    elif isinstance(value, float):
        key_value["double_value"] = value

    else:
        raise Exception(
            "Invalid type {} of value {}".format(type(value), value)
        )

    return key_value


# pylint: disable=no-member
class OTLPExporterMixin(ABC):
    """OTLP span exporter

    Args:
        endpoint: OpenTelemetry Collector receiver endpoint
        credentials: Credentials object for server authentication
        metadata: Metadata to send when exporting
    """

    def __init__(
        self,
        endpoint="localhost:55678",
        credentials: ChannelCredentials = None,
        metadata=None,
    ):
        super().__init__()

        self._metadata = metadata
        self._collector_span_kwargs = None

        if credentials is None:
            self._client = self._stub(insecure_channel(endpoint))
        else:
            self._client = self._stub(secure_channel(endpoint, credentials))

    @abstractmethod
    def _translate_data(self, data):
        pass

    def _export(self, data):
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

                    logger.debug("Waiting %ss before retrying export of span")
                    sleep(delay)
                    continue

                if error.code() == StatusCode.OK:
                    return self._result.SUCCESS

                return self.result.FAILURE

        return self._result.FAILURE
