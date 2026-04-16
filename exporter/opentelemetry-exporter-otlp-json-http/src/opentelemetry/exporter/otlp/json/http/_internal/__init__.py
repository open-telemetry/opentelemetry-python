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

from __future__ import annotations

import gzip
import logging
import os
import random
import threading
import time
import zlib
from http import HTTPStatus
from io import BytesIO
from typing import Final

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

_MAX_RETRIES: Final[int] = 6
_DEFAULT_ENDPOINT: Final[str] = "http://localhost:4318/"
_DEFAULT_TIMEOUT: Final[int] = 10
_DEFAULT_JITTER: Final[float] = 0.2


class _OTLPHttpClient:
    """A signal-agnostic OTLP HTTP client using urllib3."""

    def __init__(
        self,
        endpoint: str,
        headers: dict[str, str],
        timeout: float,
        compression: Compression,
        certificate: str | bool | None = None,
        client_key_file: str | None = None,
        client_certificate_file: str | None = None,
        jitter: float = _DEFAULT_JITTER,
    ):
        self._endpoint = endpoint
        self._headers = headers
        self._timeout = timeout
        self._compression = compression
        self._jitter = jitter
        self._shutdown = False
        self._shutdown_in_progress = threading.Event()

        pool_kwargs = {
            "retries": False,
            "cert_file": client_certificate_file,
            "key_file": client_key_file,
        }
        if certificate is False:
            pool_kwargs["cert_reqs"] = "CERT_NONE"
        elif certificate and isinstance(certificate, str):
            pool_kwargs["ca_certs"] = certificate

        self._http = urllib3.PoolManager(
            **pool_kwargs,
        )

    def _get_backoff_with_jitter(self, retry_num: int) -> float:
        """Calculate jittered exponential backoff."""
        base_backoff = 2**retry_num
        if self._jitter == 0:
            return float(base_backoff)
        return base_backoff * random.uniform(
            1 - self._jitter, 1 + self._jitter
        )

    def export(self, body: bytes, timeout: float | None = None) -> bool:
        """Exports opaque bytes to the configured endpoint."""
        if self._shutdown:
            return False

        if self._compression == Compression.GZIP:
            gzip_data = BytesIO()
            with gzip.GzipFile(fileobj=gzip_data, mode="wb") as gzip_stream:
                gzip_stream.write(body)
            body = gzip_data.getvalue()
        elif self._compression == Compression.DEFLATE:
            body = zlib.compress(body)

        if timeout is None:
            timeout = self._timeout
        deadline = time.time() + timeout
        for retry_num in range(_MAX_RETRIES):
            backoff = self._get_backoff_with_jitter(retry_num)
            status_code: int | None = None
            try:
                response = self._http.request(
                    "POST",
                    self._endpoint,
                    body=body,
                    headers=self._headers,
                    timeout=deadline - time.time(),
                    retries=False,
                )
                if 200 <= response.status < 300:
                    return True

                status_code = response.status
                retryable = _is_retryable(response.status)
                reason = response.status
            # pylint: disable-next=broad-exception-caught
            except Exception as error:
                retryable = isinstance(error, urllib3.exceptions.TimeoutError)
                reason = error

            if (
                not retryable
                or (retry_num + 1 == _MAX_RETRIES)
                or (time.time() + backoff > deadline)
                or self._shutdown
            ):
                _logger.error(
                    "Failed to export batch, code: %s, reason: %s",
                    status_code,
                    reason,
                )
                return False

            _logger.warning(
                "Transient error %s encountered while exporting, retrying in %.2fs.",
                reason,
                backoff,
            )
            if self._shutdown_in_progress.wait(backoff):
                break

        return False

    def shutdown(self):
        self._shutdown = True
        self._shutdown_in_progress.set()
        self._http.clear()


def _is_retryable(status_code: int) -> bool:
    return status_code in (
        HTTPStatus.TOO_MANY_REQUESTS,
        HTTPStatus.BAD_GATEWAY,
        HTTPStatus.SERVICE_UNAVAILABLE,
        HTTPStatus.GATEWAY_TIMEOUT,
    )


def _resolve_endpoint(endpoint_env_var: str, default_path: str) -> str:
    if endpoint := os.environ.get(endpoint_env_var):
        return endpoint

    base_endpoint = os.environ.get(
        OTEL_EXPORTER_OTLP_ENDPOINT, _DEFAULT_ENDPOINT
    )

    return f"{base_endpoint.removesuffix('/')}/{default_path}"


def _resolve_headers(
    headers: dict[str, str] | None,
    headers_env_var: str,
) -> dict[str, str]:
    headers_ = {
        "Content-Type": "application/json",
        "User-Agent": "OTel-OTLP-JSON-Exporter-Python/" + __version__,
    }
    env_headers = parse_env_headers(
        os.environ.get(
            headers_env_var, os.environ.get(OTEL_EXPORTER_OTLP_HEADERS, "")
        ),
        liberal=True,
    )
    headers_.update(env_headers)
    if headers:
        headers_.update(headers)
    return headers_


def _resolve_timeout(
    timeout: float | None,
    timeout_env_var: str,
) -> float:
    if timeout is not None:
        return timeout
    return float(
        os.environ.get(
            timeout_env_var,
            os.environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, _DEFAULT_TIMEOUT),
        )
    )


def _resolve_compression(
    compression: Compression | None, compression_env_var: str
) -> Compression:
    if compression is not None:
        return compression

    val = (
        os.environ.get(
            compression_env_var,
            os.environ.get(OTEL_EXPORTER_OTLP_COMPRESSION, "none"),
        )
        .lower()
        .strip()
    )

    try:
        return Compression(val)
    except ValueError:
        _logger.warning("Unsupported compression type: %s", val)
        return Compression.NO_COMPRESSION
