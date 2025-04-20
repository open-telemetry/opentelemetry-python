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

"""OTLP Log Exporter for OpenTelemetry."""

import gzip
import json
import logging
import zlib
from io import BytesIO
from os import environ
from time import sleep
from typing import Dict, Optional, Sequence

import requests

from opentelemetry.exporter.otlp.json.common._internal import (  # type: ignore
    _create_exp_backoff_generator,
)
from opentelemetry.exporter.otlp.json.common._log_encoder import (
    encode_logs,  # type: ignore
)
from opentelemetry.exporter.otlp.json.http import (
    _OTLP_JSON_HTTP_HEADERS,
    Compression,
)
from opentelemetry.sdk._logs import LogData
from opentelemetry.sdk._logs.export import (
    LogExporter,
    LogExportResult,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_LOGS_COMPRESSION,
    OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
    OTEL_EXPORTER_OTLP_LOGS_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_TIMEOUT,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.util.re import parse_env_headers

_logger = logging.getLogger(__name__)


DEFAULT_COMPRESSION = Compression.NoCompression
DEFAULT_ENDPOINT = "http://localhost:4318/"
DEFAULT_LOGS_EXPORT_PATH = "v1/logs"
DEFAULT_TIMEOUT = 10  # in seconds


class OTLPLogExporter(LogExporter):
    """OTLP log exporter for JSON over HTTP.

    Args:
        endpoint: The endpoint to send requests to. The default is
            "http://localhost:4318/v1/logs"
        certificate_file: Path to the CA certificate file to validate peers against.
            If None or True, the default certificates will be used.
            If False, peers will not be validated.
        client_key_file: Path to client private key file for TLS client auth.
        client_certificate_file: Path to client certificate file for TLS client auth.
        headers: Map of additional HTTP headers to add to requests.
        timeout: The maximum amount of time to wait for an export to complete.
            The default is 10 seconds.
        compression: Compression method to use for payloads.
            The default is None, which means no compression will be used.
        session: Session to use for the HTTP requests. If None, a new session
            will be created for each export.
    """

    _MAX_RETRY_TIMEOUT = 64

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        endpoint: Optional[str] = None,
        certificate_file: Optional[str] = None,
        client_key_file: Optional[str] = None,
        client_certificate_file: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
        session: Optional[requests.Session] = None,
    ):
        self._endpoint = endpoint or environ.get(
            OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
            _append_logs_path(
                environ.get(OTEL_EXPORTER_OTLP_ENDPOINT, DEFAULT_ENDPOINT)
            ),
        )
        # Keeping these as instance variables because they are used in tests
        self._certificate_file = certificate_file or environ.get(
            OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
            environ.get(OTEL_EXPORTER_OTLP_CERTIFICATE, True),
        )
        self._client_key_file = client_key_file or environ.get(
            OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_KEY, None),
        )
        self._client_certificate_file = client_certificate_file or environ.get(
            OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE, None),
        )
        self._client_cert = (
            (self._client_certificate_file, self._client_key_file)
            if self._client_certificate_file and self._client_key_file
            else self._client_certificate_file
        )
        headers_string = environ.get(
            OTEL_EXPORTER_OTLP_LOGS_HEADERS,
            environ.get(OTEL_EXPORTER_OTLP_HEADERS, ""),
        )
        self._headers = headers or parse_env_headers(
            headers_string, liberal=True
        )
        self._timeout = timeout or int(
            environ.get(
                OTEL_EXPORTER_OTLP_LOGS_TIMEOUT,
                environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, DEFAULT_TIMEOUT),
            )
        )
        self._compression = compression or _compression_from_env()
        self._session = session or requests.Session()
        self._session.headers.update(self._headers)
        self._session.headers.update(_OTLP_JSON_HTTP_HEADERS)
        if self._compression is not Compression.NoCompression:
            self._session.headers.update(
                {"Content-Encoding": self._compression.value}
            )
        self._shutdown = False

    def _export(self, serialized_data: bytes):
        data = serialized_data
        if self._compression == Compression.Gzip:
            gzip_data = BytesIO()
            with gzip.GzipFile(fileobj=gzip_data, mode="w") as gzip_stream:
                gzip_stream.write(serialized_data)
            data = gzip_data.getvalue()
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

    def export(self, batch: Sequence[LogData]) -> LogExportResult:
        """Export logs to OTLP collector via JSON over HTTP.

        Args:
            batch: The list of log data to export.

        Returns:
            The result of the export.
        """
        # After the call to Shutdown subsequent calls to Export are
        # not allowed and should return a Failure result.
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return LogExportResult.FAILURE

        # Use the proper encoder that follows ProtoJSON format
        json_logs = encode_logs(batch)
        serialized_data = json.dumps(json_logs).encode("utf-8")

        for delay in _create_exp_backoff_generator(
            max_value=self._MAX_RETRY_TIMEOUT
        ):
            if delay == self._MAX_RETRY_TIMEOUT:
                return LogExportResult.FAILURE

            resp = self._export(serialized_data)
            # pylint: disable=no-else-return
            if resp.ok:
                return LogExportResult.SUCCESS
            elif self._retryable(resp):
                _logger.warning(
                    "Transient error %s encountered while exporting logs batch, retrying in %ss.",
                    resp.reason,
                    delay,
                )
                sleep(delay)
                continue
            else:
                _logger.error(
                    "Failed to export logs batch code: %s, reason: %s",
                    resp.status_code,
                    resp.text,
                )
                return LogExportResult.FAILURE
        return LogExportResult.FAILURE

    @staticmethod
    def force_flush(timeout_millis: float = 10_000) -> bool:
        """Force flush is not implemented for this exporter.

        This method is kept for API compatibility. It does nothing.

        Args:
            timeout_millis: The maximum amount of time to wait for logs to be
                exported.

        Returns:
            True, because nothing was buffered.
        """
        return True

    def shutdown(self):
        """Shuts down the exporter.

        Called when the SDK is shut down.
        """
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._session.close()
        self._shutdown = True


def _compression_from_env() -> Compression:
    compression = (
        environ.get(
            OTEL_EXPORTER_OTLP_LOGS_COMPRESSION,
            environ.get(OTEL_EXPORTER_OTLP_COMPRESSION, "none"),
        )
        .lower()
        .strip()
    )
    return Compression(compression)


def _append_logs_path(endpoint: str) -> str:
    if endpoint.endswith("/"):
        return endpoint + DEFAULT_LOGS_EXPORT_PATH
    return endpoint + f"/{DEFAULT_LOGS_EXPORT_PATH}"
