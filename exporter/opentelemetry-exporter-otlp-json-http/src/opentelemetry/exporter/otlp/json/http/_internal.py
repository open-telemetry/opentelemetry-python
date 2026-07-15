# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from typing import TYPE_CHECKING, Literal

from opentelemetry.exporter.http.transport._urllib3 import Urllib3HTTPTransport
from opentelemetry.exporter.otlp.common.http import Compression
from opentelemetry.exporter.otlp.json.http.version import __version__
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
    from opentelemetry.exporter.http.transport import BaseHTTPTransportFactory
    from opentelemetry.exporter.http.transport._base import BaseHTTPTransport

_DEFAULT_ENDPOINT = "http://localhost:4318"
_DEFAULT_TIMEOUT = 10

_logger = logging.getLogger(__name__)


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
    headers_ = {
        "content-type": "application/json",
        "user-agent": "OTel-OTLP-JSON-Exporter-Python/" + __version__,
    }
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


def _resolve_compression(compression_env_var: str) -> Compression:
    val = (
        (
            os.environ.get(
                compression_env_var,
            )
            or os.environ.get(OTEL_EXPORTER_OTLP_COMPRESSION)
            or "none"
        )
        .lower()
        .strip()
    )

    try:
        return Compression.from_str(val)
    except ValueError:
        _logger.warning("Unsupported compression type: %s", val)
        return Compression.NONE


def _build_transport(
    certificate_file: str | None,
    client_key_file: str | None,
    client_certificate_file: str | None,
    certificate_env_var: str,
    client_key_env_var: str,
    client_certificate_env_var: str,
    transport_factory: BaseHTTPTransportFactory = Urllib3HTTPTransport,
) -> BaseHTTPTransport:
    verify: bool | str = (
        certificate_file
        or os.environ.get(
            certificate_env_var,
        )
        or os.environ.get(OTEL_EXPORTER_OTLP_CERTIFICATE)
        or True
    )
    client_key_file = (
        client_key_file
        or os.environ.get(
            client_key_env_var,
        )
        or os.environ.get(OTEL_EXPORTER_OTLP_CLIENT_KEY)
    )
    client_certificate_file = (
        client_certificate_file
        or os.environ.get(
            client_certificate_env_var,
        )
        or os.environ.get(OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE)
    )
    return transport_factory(
        verify=verify,
        cert=(client_certificate_file, client_key_file)
        if client_certificate_file and client_key_file
        else client_certificate_file,
    )
