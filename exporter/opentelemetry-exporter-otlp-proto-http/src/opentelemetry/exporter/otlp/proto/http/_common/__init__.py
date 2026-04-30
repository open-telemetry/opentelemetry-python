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
import random
import threading
import zlib
from dataclasses import dataclass
from io import BytesIO
from os import environ
from time import time
from typing import Any, Dict, Optional, Tuple, Union
from urllib.parse import urlparse

import requests
from requests.exceptions import ConnectionError

from opentelemetry.exporter.otlp.proto.common._exporter_metrics import (
    ExporterMetrics,
)
from opentelemetry.exporter.otlp.proto.http import (
    _OTLP_HTTP_HEADERS,
    Compression,
)
from opentelemetry.metrics import MeterProvider
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER,
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)
from opentelemetry.semconv.attributes.http_attributes import (
    HTTP_RESPONSE_STATUS_CODE,
)
from opentelemetry.util._importlib_metadata import entry_points
from opentelemetry.util.re import parse_env_headers

_logger = logging.getLogger(__name__)

_MAX_RETRIES = 6

DEFAULT_COMPRESSION = Compression.NoCompression
DEFAULT_ENDPOINT = "http://localhost:4318/"
DEFAULT_TIMEOUT = 10  # in seconds


def _is_retryable(resp: requests.Response) -> bool:
    if resp.status_code == 408:
        return True
    if resp.status_code >= 500 and resp.status_code <= 599:
        return True
    return False


def _load_session_from_envvar(
    cred_envvar: str,
) -> Optional[requests.Session]:
    _credential_env = environ.get(
        _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER
    ) or environ.get(cred_envvar)
    if _credential_env:
        try:
            maybe_session = next(
                iter(
                    entry_points(
                        group="opentelemetry_otlp_credential_provider",
                        name=_credential_env,
                    )
                )
            ).load()()
        except StopIteration:
            raise RuntimeError(
                f"Requested component '{_credential_env}' not found in "
                f"entry point 'opentelemetry_otlp_credential_provider'"
            )
        if isinstance(maybe_session, requests.Session):
            return maybe_session
        else:
            raise RuntimeError(
                f"Requested component '{_credential_env}' is of type {type(maybe_session)}"
                f" must be of type `requests.Session`."
            )
    return None


def _setup_session(
    session: Optional[requests.Session],
    cred_envvar: str,
    headers: Dict[str, str],
    compression: Compression,
) -> requests.Session:
    configured_session = (
        session or _load_session_from_envvar(cred_envvar) or requests.Session()
    )
    configured_session.headers.update(headers)
    configured_session.headers.update(_OTLP_HTTP_HEADERS)
    # let users override our defaults
    configured_session.headers.update(headers)
    if compression is not Compression.NoCompression:
        configured_session.headers.update(
            {"Content-Encoding": compression.value}
        )
    return configured_session


def _export(
    session: requests.Session,
    endpoint: str,
    serialized_data: bytes,
    compression: Compression,
    certificate_file: Union[str, bool],
    client_cert: Optional[Union[str, Tuple[str, str]]],
    timeout_sec: float,
) -> requests.Response:
    data = serialized_data
    if compression == Compression.Gzip:
        gzip_data = BytesIO()
        with gzip.GzipFile(fileobj=gzip_data, mode="w") as gzip_stream:
            gzip_stream.write(serialized_data)
        data = gzip_data.getvalue()
    elif compression == Compression.Deflate:
        data = zlib.compress(serialized_data)

    # By default, keep-alive is enabled in Session's request
    # headers. Backends may choose to close the connection
    # while a post happens which causes an unhandled
    # exception. This try/except will retry the post on such exceptions
    try:
        resp = session.post(
            url=endpoint,
            data=data,
            verify=certificate_file,
            timeout=timeout_sec,
            cert=client_cert,
        )
    except ConnectionError:
        resp = session.post(
            url=endpoint,
            data=data,
            verify=certificate_file,
            timeout=timeout_sec,
            cert=client_cert,
        )
    return resp


def _export_with_retries(
    session: requests.Session,
    endpoint: str,
    serialized_data: bytes,
    compression: Compression,
    certificate_file: Union[str, bool],
    client_cert: Optional[Union[str, Tuple[str, str]]],
    timeout: float,
    shutdown_event: threading.Event,
    result: Any,
    batch_name: str,
) -> bool:
    deadline_sec = time() + timeout
    for retry_num in range(_MAX_RETRIES):
        # multiplying by a random number between .8 and 1.2 introduces a +/20% jitter to each backoff.
        backoff_seconds = 2**retry_num * random.uniform(0.8, 1.2)
        export_error: Optional[Exception] = None
        try:
            resp = _export(
                session,
                endpoint,
                serialized_data,
                compression,
                certificate_file,
                client_cert,
                deadline_sec - time(),
            )
            if resp.ok:
                return True
        except requests.exceptions.RequestException as error:
            reason = error
            export_error = error
            retryable = isinstance(error, ConnectionError)
            status_code = None
        else:
            reason = resp.reason
            retryable = _is_retryable(resp)
            status_code = resp.status_code

        error_attrs = (
            {HTTP_RESPONSE_STATUS_CODE: status_code}
            if status_code is not None
            else None
        )

        if not retryable:
            _logger.error(
                "Failed to export %s batch code: %s, reason: %s",
                batch_name,
                status_code,
                reason,
            )
            result.error = export_error
            result.error_attrs = error_attrs
            return False

        if (
            retry_num + 1 == _MAX_RETRIES
            or backoff_seconds > (deadline_sec - time())
            or shutdown_event.is_set()
        ):
            _logger.error(
                "Failed to export %s batch due to timeout, "
                "max retries or shutdown.",
                batch_name,
            )
            result.error = export_error
            result.error_attrs = error_attrs
            return False

        _logger.warning(
            "Transient error %s encountered while exporting %s batch, retrying in %.2fs.",
            reason,
            batch_name,
            backoff_seconds,
        )
        if shutdown_event.wait(backoff_seconds):
            _logger.warning("Shutdown in progress, aborting retry.")
            break
    return False


def _compression_from_env(signal_compression_envvar: str) -> Compression:
    compression = (
        environ.get(
            signal_compression_envvar,
            environ.get(OTEL_EXPORTER_OTLP_COMPRESSION, "none"),
        )
        .lower()
        .strip()
    )
    return Compression(compression)


def _append_signal_path(endpoint: str, signal_path: str) -> str:
    if endpoint.endswith("/"):
        return endpoint + signal_path
    return endpoint + f"/{signal_path}"


@dataclass(frozen=True)
class _SignalConfig:
    endpoint_envvar: str
    certificate_envvar: str
    client_key_envvar: str
    client_certificate_envvar: str
    headers_envvar: str
    timeout_envvar: str
    compression_envvar: str
    credential_envvar: str
    default_export_path: str
    component_type: OtelComponentTypeValues
    signal_name: str


class OTLPHttpClient:
    def __init__(
        self,
        endpoint: Optional[str],
        certificate_file: Optional[str],
        client_key_file: Optional[str],
        client_certificate_file: Optional[str],
        headers: Optional[Dict[str, str]],
        timeout: Optional[float],
        compression: Optional[Compression],
        session: Optional[requests.Session],
        meter_provider: Optional[MeterProvider],
        signal_config: _SignalConfig,
    ):
        self._shutdown_in_progress = threading.Event()
        self._endpoint = endpoint or environ.get(
            signal_config.endpoint_envvar,
            _append_signal_path(
                environ.get(OTEL_EXPORTER_OTLP_ENDPOINT, DEFAULT_ENDPOINT),
                signal_config.default_export_path,
            ),
        )
        self._certificate_file = certificate_file or environ.get(
            signal_config.certificate_envvar,
            environ.get(OTEL_EXPORTER_OTLP_CERTIFICATE, True),
        )
        self._client_key_file = client_key_file or environ.get(
            signal_config.client_key_envvar,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_KEY, None),
        )
        self._client_certificate_file = client_certificate_file or environ.get(
            signal_config.client_certificate_envvar,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE, None),
        )
        self._client_cert = (
            (self._client_certificate_file, self._client_key_file)
            if self._client_certificate_file and self._client_key_file
            else self._client_certificate_file
        )
        headers_string = environ.get(
            signal_config.headers_envvar,
            environ.get(OTEL_EXPORTER_OTLP_HEADERS, ""),
        )
        self._headers = headers or parse_env_headers(
            headers_string, liberal=True
        )
        self._timeout = timeout or float(
            environ.get(
                signal_config.timeout_envvar,
                environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, DEFAULT_TIMEOUT),
            )
        )
        self._compression = compression or _compression_from_env(
            signal_config.compression_envvar
        )
        self._session = _setup_session(
            session,
            signal_config.credential_envvar,
            self._headers,
            self._compression,
        )
        self._shutdown = False
        self._metrics = ExporterMetrics(
            signal_config.component_type,
            signal_config.signal_name,
            urlparse(self._endpoint),
            meter_provider,
        )
