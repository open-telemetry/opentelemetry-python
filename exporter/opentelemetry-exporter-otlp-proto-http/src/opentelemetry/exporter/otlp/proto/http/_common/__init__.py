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
from io import BytesIO
from os import environ
from time import time
from typing import Any, Dict, Literal, Optional, Tuple, Union

import requests
from requests.exceptions import ConnectionError

from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER,
    OTEL_EXPORTER_OTLP_COMPRESSION,
)
from opentelemetry.exporter.otlp.proto.http import (
    _OTLP_HTTP_HEADERS,
    Compression,
)
from opentelemetry.semconv.attributes.http_attributes import (
    HTTP_RESPONSE_STATUS_CODE,
)
from opentelemetry.util._importlib_metadata import entry_points

_logger = logging.getLogger(__name__)

DEFAULT_COMPRESSION = Compression.NoCompression
DEFAULT_ENDPOINT = "http://localhost:4318/"
DEFAULT_TIMEOUT = 10  # in seconds
_MAX_RETRYS = 6


def _is_retryable(resp: requests.Response) -> bool:
    if resp.status_code == 408:
        return True
    if resp.status_code >= 500 and resp.status_code <= 599:
        return True
    return False


def _load_session_from_envvar(
    cred_envvar: Literal[
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER",
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER",
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_METRICS_CREDENTIAL_PROVIDER",
    ],
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


def setup_session(
    session: Optional[requests.Session],
    cred_envvar: Literal[
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER",
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER",
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_METRICS_CREDENTIAL_PROVIDER",
    ],
    headers: Dict[str, str],
    compression: Compression,
) -> requests.Session:
    configured_session = (
        session
        or _load_session_from_envvar(cred_envvar)
        or requests.Session()
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
    for retry_num in range(_MAX_RETRYS):
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
            retry_num + 1 == _MAX_RETRYS
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


def _compression_from_env(
    signal_compression_envvar: Literal[
        "OTEL_EXPORTER_OTLP_LOGS_COMPRESSION",
        "OTEL_EXPORTER_OTLP_METRICS_COMPRESSION",
        "OTEL_EXPORTER_OTLP_TRACES_COMPRESSION",
    ],
) -> Compression:
    compression = (
        environ.get(
            signal_compression_envvar,
            environ.get(OTEL_EXPORTER_OTLP_COMPRESSION, "none"),
        )
        .lower()
        .strip()
    )
    return Compression(compression)
