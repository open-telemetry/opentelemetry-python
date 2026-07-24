# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import math
import time
from datetime import timezone
from email.utils import parsedate_to_datetime
from http import HTTPStatus
from os import environ
from typing import Literal

import requests

from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER,
)
from opentelemetry.util._importlib_metadata import entry_points

# 64 MiB, in bytes.
_DEFAULT_MAX_REQUEST_SIZE = 64 * 1024 * 1024

# The OTLP specification lists exactly these response codes as retryable and
# requires that all other 4xx and 5xx codes are not retried.
_RETRYABLE_STATUS_CODES = frozenset(
    {
        HTTPStatus.TOO_MANY_REQUESTS.value,
        HTTPStatus.BAD_GATEWAY.value,
        HTTPStatus.SERVICE_UNAVAILABLE.value,
        HTTPStatus.GATEWAY_TIMEOUT.value,
    }
)


class RequestPayloadTooLargeError(Exception):
    """A serialized OTLP request exceeded the configured ``max_request_size``.

    The class name is emitted as the ``error.type`` attribute on the exporter's
    failed-export metric, so renaming it changes observable telemetry.
    """


def _is_retryable(resp: requests.Response) -> bool:
    return resp.status_code in _RETRYABLE_STATUS_CODES


def _extract_retry_after(resp: requests.Response) -> float | None:
    """Parse the ``Retry-After`` header (RFC 7231) into a delay in seconds.

    Returns ``None`` when the header is absent or cannot be interpreted, in
    which case the caller falls back to exponential backoff. A delay that has
    already elapsed is returned as ``0.0``, meaning retry immediately.
    """
    value = resp.headers.get("Retry-After")
    if value is None:
        return None
    value = value.strip()

    # delay-seconds: a non-negative decimal integer.
    try:
        seconds = float(value)
    except ValueError:
        pass
    else:
        return max(seconds, 0.0) if math.isfinite(seconds) else None

    # HTTP-date: wait until the indicated absolute time.
    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    return max(retry_at.timestamp() - time.time(), 0.0)


def _is_request_too_large(
    serialized_data: bytes, max_request_size: int
) -> bool:
    """Return True if the serialized request exceeds a positive size limit.

    The size is measured on the uncompressed serialized request, matching the
    OTLP specification's "before compression" request-size limit. A
    ``max_request_size`` of ``0`` (or any non-positive value) disables the
    check.
    """
    return max_request_size > 0 and len(serialized_data) > max_request_size


def _load_session_from_envvar(
    cred_envvar: Literal[
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER",
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER",
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_METRICS_CREDENTIAL_PROVIDER",
    ],
) -> requests.Session | None:
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
