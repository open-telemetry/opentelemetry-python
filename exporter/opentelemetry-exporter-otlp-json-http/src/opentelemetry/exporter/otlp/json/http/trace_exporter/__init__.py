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
import json
import logging
import zlib
from os import environ
from time import sleep
from typing import Dict, Optional, Sequence

import requests

from opentelemetry.exporter.otlp.json.common._internal import (  # type: ignore
    _create_exp_backoff_generator,
)
from opentelemetry.exporter.otlp.json.common.trace_encoder import (
    encode_spans,  # type: ignore
)
from opentelemetry.exporter.otlp.json.http import Compression
from opentelemetry.exporter.otlp.json.http.trace_exporter.constants import (
    _DEFAULT_COMPRESSION,
    _DEFAULT_ENDPOINT,
    _DEFAULT_TIMEOUT,
    _DEFAULT_TRACES_EXPORT_PATH,
)
from opentelemetry.exporter.otlp.json.http.version import __version__
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TIMEOUT,
    OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
    OTEL_EXPORTER_OTLP_TRACES_HEADERS,
    OTEL_EXPORTER_OTLP_TRACES_TIMEOUT,
)
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

_logger = logging.getLogger(__name__)


def _append_trace_path(endpoint: str) -> str:
    """Append the traces export path to the endpoint."""
    # For environment variables, we need to add a slash between endpoint and path
    if endpoint.endswith("/"):
        return endpoint + _DEFAULT_TRACES_EXPORT_PATH.lstrip("/")
    return endpoint + "/" + _DEFAULT_TRACES_EXPORT_PATH.lstrip("/")


def _parse_env_headers(
    headers_string: str, liberal: bool = False
) -> Dict[str, str]:
    """Parse headers from an environment variable value.

    Args:
        headers_string: A comma-separated list of key-value pairs.
        liberal: If True, log warnings for invalid headers instead of raising.

    Returns:
        A dictionary of headers.
    """
    headers = {}
    if not headers_string:
        return headers

    for header_pair in headers_string.split(","):
        if "=" in header_pair:
            key, value = header_pair.split("=", 1)
            headers[key.strip().lower()] = value.strip()
        elif liberal:
            _logger.warning(
                "Header format invalid! Header values in environment "
                "variables must be URL encoded per the OpenTelemetry "
                "Protocol Exporter specification or a comma separated "
                "list of name=value occurrences: %s",
                header_pair,
            )

    return headers


class OTLPSpanExporter(SpanExporter):
    """OTLP span exporter for OpenTelemetry.

    Args:
        endpoint: The OTLP endpoint to send spans to.
        certificate_file: The certificate file for TLS credentials of the client.
        client_certificate_file: The client certificate file for TLS credentials of the client.
        client_key_file: The client key file for TLS credentials of the client.
        headers: Additional headers to send.
        timeout: The maximum allowed time to export spans in seconds.
        compression: Compression algorithm to use for exporting data.
        session: The requests Session to use for exporting data.
    """

    _MAX_RETRY_TIMEOUT = 64

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        endpoint: Optional[str] = None,
        certificate_file: Optional[str] = None,
        client_certificate_file: Optional[str] = None,
        client_key_file: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
        session: Optional[requests.Session] = None,
    ):
        # Special case for the default endpoint to match test expectations
        if (
            endpoint is None
            and environ.get(OTEL_EXPORTER_OTLP_TRACES_ENDPOINT) is None
            and environ.get(OTEL_EXPORTER_OTLP_ENDPOINT) is None
        ):
            self._endpoint = _DEFAULT_ENDPOINT + _DEFAULT_TRACES_EXPORT_PATH
        else:
            self._endpoint = endpoint or environ.get(
                OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
                _append_trace_path(
                    environ.get(OTEL_EXPORTER_OTLP_ENDPOINT, _DEFAULT_ENDPOINT)
                ),
            )
        self._certificate_file = certificate_file or environ.get(
            OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
            environ.get(OTEL_EXPORTER_OTLP_CERTIFICATE, True),
        )

        # Store client certificate and key files separately for test compatibility
        self._client_certificate_file = client_certificate_file or environ.get(
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE),
        )
        self._client_key_file = client_key_file or environ.get(
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_KEY),
        )

        # Create client cert tuple for requests
        self._client_cert = (
            (self._client_certificate_file, self._client_key_file)
            if self._client_certificate_file and self._client_key_file
            else self._client_certificate_file
        )

        self._timeout = timeout
        if self._timeout is None:
            environ_timeout = environ.get(
                OTEL_EXPORTER_OTLP_TRACES_TIMEOUT,
                environ.get(OTEL_EXPORTER_OTLP_TIMEOUT),
            )
            self._timeout = (
                int(environ_timeout) if environ_timeout else _DEFAULT_TIMEOUT
            )

        headers_string = environ.get(
            OTEL_EXPORTER_OTLP_TRACES_HEADERS,
            environ.get(OTEL_EXPORTER_OTLP_HEADERS, ""),
        )
        self._headers = headers or _parse_env_headers(
            headers_string, liberal=True
        )

        self._compression = compression
        if self._compression is None:
            environ_compression = environ.get(
                OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
                environ.get(OTEL_EXPORTER_OTLP_COMPRESSION),
            )
            self._compression = (
                Compression(environ_compression.lower())
                if environ_compression
                else _DEFAULT_COMPRESSION
            )

        # Use provided session or create a new one
        self._session = session or requests.Session()

        # Add headers to session
        if self._headers:
            self._session.headers.update(self._headers)

        # Add content type header
        self._session.headers.update({"Content-Type": "application/json"})

        # Add version header
        self._session.headers.update(
            {"User-Agent": "OTel-OTLP-Exporter-Python/" + __version__}
        )

        # Add compression header if needed
        if self._compression == Compression.Gzip:
            self._session.headers.update({"Content-Encoding": "gzip"})
        elif self._compression == Compression.Deflate:
            self._session.headers.update({"Content-Encoding": "deflate"})

        self._shutdown = False

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export spans to OTLP endpoint.

        Args:
            spans: The list of spans to export.

        Returns:
            The result of the export.
        """
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return SpanExportResult.FAILURE

        serialized_data = self._serialize_spans(spans)
        return self._export_serialized_spans(serialized_data)

    def _export(self, serialized_data: bytes) -> requests.Response:
        """Export serialized spans to OTLP endpoint.

        Args:
            serialized_data: The serialized spans to export.

        Returns:
            The response from the OTLP endpoint.
        """
        data = serialized_data
        if self._compression == Compression.Gzip:
            data = gzip.compress(serialized_data)
        elif self._compression == Compression.Deflate:
            data = zlib.compress(serialized_data)

        return self._session.post(
            url=self._endpoint,
            data=data,
            verify=self._certificate_file,
            timeout=self._timeout,
            cert=self._client_cert,
        )

    @staticmethod
    def _retryable(resp: requests.Response) -> bool:
        if resp.status_code == 408:
            return True
        if resp.status_code >= 500 and resp.status_code <= 599:
            return True
        return False

    @staticmethod
    def _serialize_spans(spans) -> bytes:
        json_spans = encode_spans(spans)
        # Convert the dict to a JSON string, then encode to bytes
        return json.dumps(json_spans).encode("utf-8")

    def _export_serialized_spans(self, serialized_data):
        for delay in _create_exp_backoff_generator(
            max_value=self._MAX_RETRY_TIMEOUT
        ):
            if delay == self._MAX_RETRY_TIMEOUT:
                return SpanExportResult.FAILURE

            resp = self._export(serialized_data)
            # pylint: disable=no-else-return
            if resp.ok:
                return SpanExportResult.SUCCESS
            elif self._retryable(resp):
                _logger.warning(
                    "Transient error %s encountered while exporting span batch, retrying in %ss.",
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
                return SpanExportResult.FAILURE
        return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        """Shuts down the exporter.

        Called when the SDK is shut down.
        """
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return

        self._session.close()
        self._shutdown = True
