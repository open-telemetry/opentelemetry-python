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

import logging
from time import sleep
from typing import List, Optional, Tuple

from backoff import expo
from google.rpc.error_details_pb2 import RetryInfo
from grpc import (
    Compression,
    RpcError,
    StatusCode,
    insecure_channel,
    secure_channel,
    ssl_channel_credentials,
)

from opentelemetry.exporter.otlp.util import Compression as OTLPCompression
from opentelemetry.exporter.otlp.util import Headers as OTLPHeaders
from opentelemetry.proto.collector.trace.v1 import trace_service_pb2_grpc
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)

logger = logging.getLogger(__name__)


class GrpcSender:
    def __init__(
        self,
        endpoint: str,
        insecure: Optional[bool] = False,
        certificate_file: Optional[str] = None,
        headers: Optional[OTLPHeaders] = None,
        timeout: Optional[int] = None,
        compression: Optional[OTLPCompression] = None,
    ):
        self._endpoint = endpoint
        self._insecure = insecure
        self._certificate_file = certificate_file
        self._headers = _parse_headers(headers)
        self._timeout = timeout
        self._compression = _determine_compression(compression)

        self._create_channel()

    # pylint: disable=no-member
    def send(self, resource_spans: ExportTraceServiceRequest) -> bool:
        # expo returns a generator that yields delay values which grow
        # exponentially. Once delay is greater than max_value, the yielded
        # value will remain constant.
        # max_value is set to 900 (900 seconds is 15 minutes) to use the same
        # value as used in the Go implementation.
        expo_max_value = 900

        for delay in expo(max_value=expo_max_value):

            if delay == expo_max_value:
                return False

            try:
                trace_service_pb2_grpc.TraceServiceStub(self._channel).Export(
                    request=resource_spans,
                    metadata=self._headers,
                    timeout=self._timeout,
                )
                return True
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
                    return True
                return False

        return False

    def _create_channel(self) -> None:
        if self._insecure:
            self._channel = insecure_channel(
                self._endpoint, compression=self._compression
            )
        else:
            if self._certificate_file is None:
                root_certificates = None
            else:
                try:
                    with open(self._certificate_file, "rb") as cert_file:
                        root_certificates = cert_file.read()
                except FileNotFoundError:
                    logger.exception(
                        "Unable to read root certificates from " "file: '%s'",
                        self._certificate_file,
                    )
                    root_certificates = None

            self._channel = secure_channel(
                self._endpoint,
                ssl_channel_credentials(root_certificates),
                compression=self._compression,
            )


def _parse_headers(
    otlp_headers: Optional[OTLPHeaders],
) -> Optional[List[Tuple[str, str]]]:
    if not otlp_headers:
        grpc_headers = None
    else:
        grpc_headers = []
        for header_key, header_value in otlp_headers.items():
            grpc_headers.append((header_key, header_value))
    return grpc_headers


def _determine_compression(
    otlp_compression: Optional[OTLPCompression],
) -> Compression:
    grpc_compression = Compression.NoCompression
    if otlp_compression:
        if otlp_compression == OTLPCompression.GZIP:
            grpc_compression = Compression.Gzip
        elif otlp_compression == OTLPCompression.DEFLATE:
            logger.warning(
                "Opentelemetry Collector does not currently "
                "support deflate compression for gRPC - "
                "defaulting to no compression"
            )
    return grpc_compression
