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
from typing import TYPE_CHECKING, Final, Literal

from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http._transport import BaseHTTPTransport
from opentelemetry.exporter.otlp.proto.http._transport._requests import (
    RequestsHTTPTransport,
)
from opentelemetry.exporter.otlp.proto.http._transport._urllib3 import (
    Urllib3HTTPTransport,
)
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
)
from opentelemetry.util._importlib_metadata import entry_points

if TYPE_CHECKING:
    import requests

_DEFAULT_ENDPOINT: Final[str] = "http://localhost:4318"


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


def _endpoint_from_env(
    signal_endpoint_envvar: Literal[
        "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT",
        "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT",
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
    ],
    default_signal_path: Literal["v1/logs", "v1/metrics", "v1/traces"],
) -> str:
    base = (
        environ.get(
            OTEL_EXPORTER_OTLP_ENDPOINT, _DEFAULT_ENDPOINT
        ).removesuffix("/")
        + "/"
    )
    return environ.get(signal_endpoint_envvar, base + default_signal_path)


def _session_from_env(
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


def _transport_from_args(
    session: requests.Session | None,
    verify: bool | str,
    cert: str | tuple[str, str] | None,
) -> BaseHTTPTransport:
    if session is not None:
        return RequestsHTTPTransport(verify=verify, cert=cert, session=session)
    return Urllib3HTTPTransport(verify=verify, cert=cert)
