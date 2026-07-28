# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from os import environ
from typing import Literal, Mapping

import requests
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER,
)
from opentelemetry.util._importlib_metadata import entry_points

# 64 MiB, in bytes.
_DEFAULT_MAX_REQUEST_SIZE = 64 * 1024 * 1024


class RequestPayloadTooLargeError(Exception):
    """A serialized OTLP request exceeded the configured ``max_request_size``.

    The class name is emitted as the ``error.type`` attribute on the exporter's
    failed-export metric, so renaming it changes observable telemetry.
    """


def _is_retryable(resp: requests.Response) -> bool:
    if resp.status_code in (408, 429):
        return True
    if 500 <= resp.status_code <= 599:
        return True
    return False


def _get_retry_after_seconds(headers: Mapping[str, str] | None) -> float | None:
    """Parse Retry-After header into seconds if present.

    Supports both delta-seconds and HTTP-date formats.
    """
    if not headers:
        return None
    value = headers.get("Retry-After")
    if not value:
        return None
    value = value.strip()
    # delta-seconds
    if value.isdigit():
        try:
            seconds = int(value)
            return max(0, float(seconds))
        except Exception:
            return None
    # HTTP-date
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = (dt - now).total_seconds()
        return max(0.0, delta)
    except Exception:
        return None


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
