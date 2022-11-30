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

import gzip
import zlib
from os import environ
from io import BytesIO
from typing import Dict, Optional, Generic, TypeVar, Sequence
from abc import ABC, abstractmethod

import requests
import backoff

from opentelemetry.exporter.otlp.proto.http import (
    _OTLP_HTTP_HEADERS,
    Compression,
)

from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_COMPRESSION,
)

SDKDataT = TypeVar("SDKDataT")
ExportResultT = TypeVar("ExportResultT")


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

class OTLPExporterMixin(ABC, Generic[SDKDataT, ExportResultT]):

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

    @abstractmethod
    def export(
        self,
        data: Sequence[SDKDataT],
        **kwargs,
    ) -> ExportResultT:
        pass


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
