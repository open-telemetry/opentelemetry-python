# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from typing import TYPE_CHECKING, Literal

from opentelemetry.exporter.http.transport._requests import (
    RequestsHTTPTransport,
)
from opentelemetry.exporter.http.transport._urllib3 import (
    Urllib3HTTPTransport,
)
from opentelemetry.exporter.otlp.common import _http
from opentelemetry.exporter.otlp.proto.http import (
    _OTLP_HTTP_HEADERS,
    Compression,
)
from opentelemetry.exporter.otlp.proto.http._common import (
    _load_session_from_envvar,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.util.re import parse_env_headers

if TYPE_CHECKING:
    import requests

    from opentelemetry.exporter.http.transport._base import BaseHTTPTransport

_logger = logging.getLogger(__name__)

_DEFAULT_ENDPOINT = "http://localhost:4318"
_DEFAULT_TIMEOUT = 10


def _normalize_compression(
    compression: Compression | _http.Compression | None,
) -> _http.Compression | None:
    if compression is None:
        return None
    match compression:
        case Compression.NoCompression:
            return _http.Compression.NONE
        case Compression.Deflate:
            return _http.Compression.DEFLATE
        case Compression.Gzip:
            return _http.Compression.GZIP
        case _:
            return compression


def _resolve_endpoint(
    endpoint_env_var: str,
    default_path: Literal["v1/traces", "v1/metrics", "v1/logs"],
) -> str:
    if endpoint := os.environ.get(endpoint_env_var):
        return endpoint

    base_endpoint = (
        os.environ.get(OTEL_EXPORTER_OTLP_ENDPOINT) or _DEFAULT_ENDPOINT
    )

    return f"{base_endpoint.removesuffix('/')}/{default_path}"


def _resolve_headers(
    headers: Mapping[str, str] | None,
    headers_env_var: str,
) -> dict[str, str]:
    headers_ = {k.lower(): v for k, v in _OTLP_HTTP_HEADERS.items()}
    env_headers = parse_env_headers(
        os.environ.get(headers_env_var)
        or os.environ.get(OTEL_EXPORTER_OTLP_HEADERS, ""),
        liberal=True,
    )
    headers_.update(env_headers)
    if headers:
        headers_.update({key.lower(): value for key, value in headers.items()})
    return headers_


def _resolve_timeout(
    timeout_env_var: str,
) -> float:
    raw = (
        os.environ.get(timeout_env_var)
        or os.environ.get(OTEL_EXPORTER_OTLP_TIMEOUT)
        or _DEFAULT_TIMEOUT
    )

    try:
        return float(raw)
    except ValueError:
        _logger.warning(
            "Invalid timeout value %r, using default of %s seconds",
            raw,
            _DEFAULT_TIMEOUT,
        )
        return float(_DEFAULT_TIMEOUT)


def _resolve_compression(compression_env_var: str) -> _http.Compression:
    value = (
        (
            os.environ.get(compression_env_var)
            or os.environ.get(OTEL_EXPORTER_OTLP_COMPRESSION)
            or "none"
        )
        .lower()
        .strip()
    )

    try:
        return _http.Compression.from_str(value)
    except ValueError:
        _logger.warning("Unsupported compression type: %s", value)
        return _http.Compression.NONE


_CredentialEnvVar = Literal[
    "OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER",
    "OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER",
    "OTEL_PYTHON_EXPORTER_OTLP_HTTP_METRICS_CREDENTIAL_PROVIDER",
]


def _resolve_session(
    session: requests.Session | None,
    credential_env_var: _CredentialEnvVar,
) -> requests.Session | None:
    """Resolve the one canonical session used by both the exporter and its transport.

    Returns ``None`` when no explicit session was supplied and no credential
    provider is configured, in which case the exporter falls back to a
    lighter-weight urllib3-backed transport instead of a requests session.
    """
    return session or _load_session_from_envvar(credential_env_var)


def _build_transport(
    certificate_file: str | bool | None,
    client_key_file: str | None,
    client_certificate_file: str | None,
    certificate_env_var: str,
    client_key_env_var: str,
    client_certificate_env_var: str,
    session: requests.Session | None,
) -> BaseHTTPTransport:
    verify: bool | str = (
        certificate_file
        or os.environ.get(certificate_env_var)
        or os.environ.get(OTEL_EXPORTER_OTLP_CERTIFICATE)
        or True
    )
    client_key_file = (
        client_key_file
        or os.environ.get(client_key_env_var)
        or os.environ.get(OTEL_EXPORTER_OTLP_CLIENT_KEY)
    )
    client_certificate_file = (
        client_certificate_file
        or os.environ.get(client_certificate_env_var)
        or os.environ.get(OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE)
    )
    cert = (
        (client_certificate_file, client_key_file)
        if client_certificate_file and client_key_file
        else client_certificate_file
    )

    if session is not None:
        return RequestsHTTPTransport(verify=verify, cert=cert, session=session)
    return Urllib3HTTPTransport(verify=verify, cert=cert)
