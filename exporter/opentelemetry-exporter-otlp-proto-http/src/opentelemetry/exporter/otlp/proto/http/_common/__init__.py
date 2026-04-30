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
from __future__ import annotations

from os import environ
from typing import TYPE_CHECKING, Literal, Mapping

from opentelemetry.exporter.otlp.proto.http import (
    _OTLP_HTTP_HEADERS,
    Compression,
)
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER,
)
from opentelemetry.util._importlib_metadata import entry_points

if TYPE_CHECKING:
    from opentelemetry.exporter.otlp.proto.http._session import (
        HttpSession,
        HttpResponse,
    )


def _is_retryable(resp: HttpResponse) -> bool:
    if resp.status_code == 408:
        return True
    if 500 <= resp.status_code <= 599:
        return True
    return False


def _load_session_from_envvar(
    cred_envvar: Literal[
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER",
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER",
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_METRICS_CREDENTIAL_PROVIDER",
    ],
) -> HttpSession | None:
    _credential_env = environ.get(
        _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER
    ) or environ.get(cred_envvar)
    if not _credential_env:
        return None
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
    if not (
        hasattr(maybe_session, "request") and hasattr(maybe_session, "close")
    ):
        raise RuntimeError(
            f"Requested component '{_credential_env}' is of type "
            f"{type(maybe_session)}; must implement the HttpSession protocol "
            f"(request() and close() methods)."
        )
    return maybe_session


def _build_default_headers(
    user_headers: Mapping[str, str], compression: Compression
) -> dict[str, str]:
    """Combine OTLP defaults with user headers; user values override."""
    merged = {**_OTLP_HTTP_HEADERS, **user_headers}
    if compression is not Compression.NoCompression:
        merged["Content-Encoding"] = compression.value
    return merged
