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
import logging
import os
import random
import threading
import time
import zlib
from io import BytesIO
from typing import Dict, Optional, Final, Union

import urllib3
from opentelemetry.exporter.otlp.json.http import Compression
from opentelemetry.exporter.otlp.json.http.version import __version__
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.util.re import parse_env_headers

_logger = logging.getLogger(__name__)

_MAX_RETRYS: Final[int] = 6
_DEFAULT_ENDPOINT: Final[str] = "http://localhost:4318/"
_DEFAULT_TIMEOUT: Final[int] = 10
_DEFAULT_JITTER: Final[float] = 0.2


class _OTLPHttpClient:
    """A signal-agnostic OTLP HTTP client using urllib3."""

    def __init__(
        self,
        endpoint: str,
        headers: Dict[str, str],
        timeout: float,
        compression: Compression,
        certificate_file: Optional[Union[str, bool]] = None,
        client_key_file: Optional[Union[str, bool]] = None,
        client_certificate_file: Optional[Union[str, bool]] = None,
        jitter: float = _DEFAULT_JITTER,
    ):
        self._endpoint = endpoint
        self._headers = headers
        self._timeout = timeout
        self._compression = compression
        self._jitter = jitter
        self._shutdown = False
        self._shutdown_in_progress = threading.Event()

        self._http = urllib3.PoolManager(
            retries=False,
            ca_certs=certificate_file,
            cert_file=client_certificate_file,
            key_file=client_key_file,
        )

    @staticmethod
    def _is_retryable(status_code: int) -> bool:
        return status_code in (408, 429) or (500 <= status_code < 600)

    def _get_backoff_with_jitter(self, retry_num: int) -> float:
        """Calculate jittered exponential backoff."""
        base_backoff = 2**retry_num
        if self._jitter == 0:
            return float(base_backoff)
        return base_backoff * random.uniform(
            1 - self._jitter, 1 + self._jitter
        )

    def export(self, body: bytes, timeout_sec: Optional[float] = None) -> bool:
        """Exports opaque bytes to the configured endpoint."""
        if self._shutdown:
            return False

        if self._compression == Compression.Gzip:
            gzip_data = BytesIO()
            with gzip.GzipFile(fileobj=gzip_data, mode="wb") as gzip_stream:
                gzip_stream.write(body)
            body = gzip_data.getvalue()
        elif self._compression == Compression.Deflate:
            body = zlib.compress(body)

        timeout = timeout_sec if timeout_sec is not None else self._timeout
        deadline_sec = time.time() + timeout
        for retry_num in range(_MAX_RETRYS):
            backoff_seconds = self._get_backoff_with_jitter(retry_num)
            try:
                response = self._http.request(
                    "POST",
                    self._endpoint,
                    body=body,
                    headers=self._headers,
                    timeout=deadline_sec - time.time(),
                    retries=False,
                )
                if 200 <= response.status < 300:
                    return True

                retryable = self._is_retryable(response.status)
                reason = response.status
            except Exception as error:
                retryable = True
                reason = error

            if (
                not retryable
                or (retry_num + 1 == _MAX_RETRYS)
                or (time.time() + backoff_seconds > deadline_sec)
                or self._shutdown
            ):
                _logger.error("Failed to export batch. Code: %s", reason)
                return False

            _logger.warning(
                "Transient error %s encountered while exporting, retrying in %.2fs.",
                reason,
                backoff_seconds,
            )
            if self._shutdown_in_progress.wait(backoff_seconds):
                break

        return False

    def shutdown(self):
        self._shutdown = True
        self._shutdown_in_progress.set()
        self._http.clear()


def _resolve_endpoint(default_path: str, signal_env: str) -> str:
    if endpoint := os.environ.get(signal_env):
        return endpoint

    base_endpoint = os.environ.get(
        OTEL_EXPORTER_OTLP_ENDPOINT, _DEFAULT_ENDPOINT
    )

    return f"{base_endpoint.removesuffix('/')}/{default_path}"


def _resolve_headers(
    signal_headers_env: str, custom_headers: Optional[Dict[str, str]]
) -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "OTel-OTLP-JSON-Exporter-Python/" + __version__,
    }
    env_headers = parse_env_headers(
        os.environ.get(
            signal_headers_env, os.environ.get(OTEL_EXPORTER_OTLP_HEADERS, "")
        ),
        liberal=True,
    )
    headers.update(env_headers)
    if custom_headers:
        headers.update(custom_headers)
    return headers


def _resolve_timeout(
    signal_timeout_env: str, custom_timeout: Optional[float]
) -> float:
    if custom_timeout is not None:
        return custom_timeout
    return float(
        os.environ.get(
            signal_timeout_env,
            os.environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, _DEFAULT_TIMEOUT),
        )
    )


def _resolve_compression(
    signal_compression_env: str, custom_compression: Optional[Compression]
) -> Compression:
    if custom_compression is not None:
        return custom_compression

    val = (
        os.environ.get(
            signal_compression_env,
            os.environ.get(OTEL_EXPORTER_OTLP_COMPRESSION, "none"),
        )
        .lower()
        .strip()
    )

    try:
        return Compression(val)
    except ValueError:
        _logger.warning("Unsupported compression type: %s", val)
        return Compression.NoCompression


def _resolve_tls_file(
    custom_file: Optional[str],
    signal_env: str,
    global_env: str,
    default: Optional[Union[str, bool]] = None,
) -> Optional[Union[str, bool]]:
    if custom_file is not None:
        return custom_file
    return os.environ.get(signal_env, os.environ.get(global_env, default))
