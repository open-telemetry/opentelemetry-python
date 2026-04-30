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

import logging
from os import environ
from typing import Literal, Optional

import requests
from google.rpc.status_pb2 import Status

from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER,
)
from opentelemetry.util._importlib_metadata import entry_points

_logger = logging.getLogger(__name__)

_CONTENT_TYPE_PROTOBUF = "application/x-protobuf"
_CONTENT_TYPE_JSON = "application/json"


def _parse_response_body(resp: requests.Response) -> str:
    """Parse an HTTP response body based on its Content-Type header.

    Per the OTLP spec, error responses (4xx/5xx) use ``google.rpc.Status``
    for protobuf bodies and the equivalent JSON representation.

    Args:
        resp: The HTTP response from the OTLP endpoint.

    Returns:
        A human-readable string describing the response body error details,
        or ``resp.reason`` if the body is empty or cannot be parsed.
    """
    if not resp.content:
        return resp.reason

    content_type = (
        resp.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    )

    if content_type == _CONTENT_TYPE_PROTOBUF:
        status = Status()
        try:
            status.ParseFromString(resp.content)
        except Exception:  # pylint: disable=broad-except
            _logger.debug(
                "Failed to parse protobuf response body", exc_info=True
            )
            return resp.reason
        if status.message:
            return status.message
        return resp.reason

    if content_type == _CONTENT_TYPE_JSON:
        try:
            body = resp.json()
        except Exception:  # pylint: disable=broad-except
            _logger.debug("Failed to parse JSON response body", exc_info=True)
            return resp.text or resp.reason
        if isinstance(body, dict):
            partial = body.get("partialSuccess")
            if isinstance(partial, dict) and (
                error_message := partial.get("errorMessage", "")
            ):
                return error_message
            # google.rpc.Status uses "message"
            if rpc_message := body.get("message", ""):
                return rpc_message

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
