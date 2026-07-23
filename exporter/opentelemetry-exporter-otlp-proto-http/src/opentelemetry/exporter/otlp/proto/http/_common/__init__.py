# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
from email.message import Message
from os import environ
from typing import Literal

import requests
from google.rpc.status_pb2 import Status

from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER,
)
from opentelemetry.util._importlib_metadata import entry_points

_logger = logging.getLogger(__name__)

_CONTENT_TYPE_PROTOBUF = "application/x-protobuf"


def _parse_response_body(resp: requests.Response) -> str:
    """Parse an HTTP response body based on its Content-Type header.

    Per the OTLP spec, error responses (4xx/5xx) MUST be a protobuf-encoded
    ``google.rpc.Status`` message.

    Args:
        resp: The HTTP response from the OTLP endpoint.

    Returns:
        A human-readable string describing the response body error details,
        or ``resp.reason`` if the body is empty or cannot be parsed.
    """
    if not resp.content:
        return resp.reason

    msg = Message()
    msg["Content-Type"] = resp.headers.get("Content-Type", "")
    content_type = msg.get_content_type()

    if content_type == _CONTENT_TYPE_PROTOBUF:
        status = Status()
        try:
            status.ParseFromString(resp.content)
        except Exception:  # pylint: disable=broad-except
            _logger.debug(
                "Failed to parse protobuf response body", exc_info=True
            )
            return resp.reason
        return status.message or resp.reason

    return resp.text.strip() or resp.reason


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
