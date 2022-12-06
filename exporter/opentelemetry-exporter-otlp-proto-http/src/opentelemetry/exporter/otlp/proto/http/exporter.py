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
import gzip
import zlib
from os import environ
from io import BytesIO
from typing import Dict, Optional, Generic, TypeVar, Sequence
from abc import ABC
from time import sleep

import requests
import backoff

from opentelemetry.exporter.otlp.proto.http import (
    _OTLP_HTTP_HEADERS,
    Compression,
)

from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_COMPRESSION,
)

_logger = logging.getLogger(__name__)

_SDKDataT = TypeVar("_SDKDataT")
_ExportResultT = TypeVar("_ExportResultT")


DEFAULT_COMPRESSION = Compression.NoCompression
DEFAULT_ENDPOINT = "http://localhost:4318/"
DEFAULT_TIMEOUT = 10  # in seconds

# Work around API change between backoff 1.x and 2.x. Since 2.0.0 the backoff
# wait generator API requires a first .send(None) before reading the backoff
# values from the generator.
_is_backoff_v2 = next(backoff.expo()) is None


def _expo(*args, **kwargs):
    gen = backoff.expo(*args, **kwargs)
    if _is_backoff_v2:
        gen.send(None)
    return gen


class _OTLPExporterMixin(ABC, Generic[_SDKDataT, _ExportResultT]):

    _MAX_RETRY_TIMEOUT = 64

    def __init__(
        self,
        endpoint: Optional[str] = None,
        certificate_file: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
        session: Optional[requests.Session] = None,
    ):
        self._endpoint = endpoint
        self._certificate_file = certificate_file

        self._headers = headers
        self._timeout = timeout
        self._compression = compression
        self._session = session or requests.Session()
        self._session.headers.update(self._headers)
        self._session.headers.update(_OTLP_HTTP_HEADERS)
        if self._compression is not Compression.NoCompression:
            self._session.headers.update(
                {"Content-Encoding": self._compression.value}
            )
        self._shutdown = False

    def _export(self, serialized_data: str):
        data = serialized_data
        if self._compression == Compression.Gzip:
            gzip_data = BytesIO()
            with gzip.GzipFile(fileobj=gzip_data, mode="w") as gzip_stream:
                gzip_stream.write(serialized_data)
            data = gzip_data.getvalue()
        elif self._compression == Compression.Deflate:
            data = zlib.compress(bytes(serialized_data))

        return self._session.post(
            url=self._endpoint,
            data=data,
            verify=self._certificate_file,
            timeout=self._timeout,
        )

    @staticmethod
    def _retryable(resp: requests.Response) -> bool:
        if resp.status_code == 408:
            return True
        if resp.status_code >= 500 and resp.status_code <= 599:
            return True
        return False

    def export(
        self,
        data: Sequence[_SDKDataT],
        **kwargs,
    ) -> _ExportResultT:
        # After the call to Shutdown subsequent calls to Export are
        # not allowed and should return a Failure result.
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return self._result.FAILURE

        serialized_data = self._encoder.serialize(data)

        for delay in _expo(max_value=self._MAX_RETRY_TIMEOUT):

            if delay == self._MAX_RETRY_TIMEOUT:
                return self._result.FAILURE

            resp = self._export(serialized_data)
            # pylint: disable=no-else-return
            if resp.status_code in (200, 202):
                return self._result.SUCCESS
            elif self._retryable(resp):
                _logger.warning(
                    "Transient error %s encountered while exporting batch, retrying in %ss.",
                    resp.reason,
                    delay,
                )
                sleep(delay)
                continue
            else:
                _logger.error(
                    "Failed to export batch code: %s, reason: %s",
                    resp.status_code,
                    resp.text,
                )
                return self._result.FAILURE
        return self._result.FAILURE


def _compression_from_env(key) -> Compression:
    compression = (
        environ.get(
            key,
            environ.get(OTEL_EXPORTER_OTLP_COMPRESSION, "none"),
        )
        .lower()
        .strip()
    )
    return Compression(compression)
