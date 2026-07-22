# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from os import environ
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
from opentelemetry.util._importlib_metadata import entry_points
from opentelemetry.util.re import parse_env_headers

if TYPE_CHECKING:
    import requests

    from opentelemetry.exporter.http.transport._base import BaseHTTPTransport

    _CredentialEnvVar = Literal[
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER",
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER",
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_METRICS_CREDENTIAL_PROVIDER",
    ]

_logger = logging.getLogger(__name__)

_DEFAULT_ENDPOINT = "http://localhost:4318"
_DEFAULT_TIMEOUT = 10


def _load_session_from_envvar(
    cred_envvar: _CredentialEnvVar,
) -> requests.Session | None:
    _credential_env = environ.get(
        _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER
    ) or environ.get(cred_envvar)
    if _credential_env:
        try:
            # pylint: disable-next=import-outside-toplevel
            import requests  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "The 'requests' package is required to load a credential "
                "provider session but is not installed. Install it with "
                "`pip install opentelemetry-exporter-otlp-proto-http[requests]` "
                "or `pip install requests`."
            ) from exc

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


def _normalize_compression(
    compression: Compression | _http.Compression | None,
) -> _http.Compression | None:
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


def _build_transport(
    certificate_file: str | None,
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

    return (
        RequestsHTTPTransport(verify=verify, cert=cert, session=session)
        if session
        else Urllib3HTTPTransport(verify=verify, cert=cert)
    )
