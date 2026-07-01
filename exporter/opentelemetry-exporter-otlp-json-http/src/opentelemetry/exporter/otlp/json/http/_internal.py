# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
import os
from collections.abc import Mapping

from opentelemetry.exporter.otlp.common import Compression
from opentelemetry.exporter.otlp.json.http.version import __version__
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.util.re import parse_env_headers

_DEFAULT_ENDPOINT = "http://localhost:4318/"
_DEFAULT_TIMEOUT = 10

_logger = logging.getLogger(__name__)


def _resolve_endpoint(endpoint_env_var: str, default_path: str) -> str:
    if endpoint := os.environ.get(endpoint_env_var):
        return endpoint

    base_endpoint = os.environ.get(
        OTEL_EXPORTER_OTLP_ENDPOINT, _DEFAULT_ENDPOINT
    )

    return f"{base_endpoint.removesuffix('/')}/{default_path}"


def _resolve_headers(
    headers: Mapping[str, str] | None,
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
    timeout_env_var: str,
) -> float:
    return float(
        os.environ.get(
            timeout_env_var,
            os.environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, _DEFAULT_TIMEOUT),
        )
    )


def _resolve_compression(compression_env_var: str) -> Compression:
    val = (
        os.environ.get(
            compression_env_var,
            os.environ.get(OTEL_EXPORTER_OTLP_COMPRESSION, "none"),
        )
        .lower()
        .strip()
    )

    try:
        return Compression.from_str(val)
    except ValueError:
        _logger.warning("Unsupported compression type: %s", val)
        return Compression.NONE
