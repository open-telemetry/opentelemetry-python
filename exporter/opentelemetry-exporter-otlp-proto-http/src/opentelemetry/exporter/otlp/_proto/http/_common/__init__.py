# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import ssl
from os import environ
from typing import Literal
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER,
)
from opentelemetry.util._importlib_metadata import entry_points


def _is_retryable(status_code: int) -> bool:
    if status_code == 408:
        return True
    if 500 <= status_code <= 599:
        return True
    return False


def _build_ssl_context(
    certificate_file: str | bool,
    client_cert: str | tuple[str, str | None] | None,
) -> ssl.SSLContext:
    context = ssl.create_default_context(
        cafile=certificate_file if isinstance(certificate_file, str) else None
    )
    if certificate_file is False:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    if client_cert:
        certfile, keyfile = (
            client_cert if isinstance(client_cert, tuple) else (client_cert, None)
        )
        context.load_cert_chain(certfile, keyfile)
    return context


def _post(
    url: str,
    data: bytes,
    headers: dict[str, str],
    timeout_sec: float,
    ssl_context: ssl.SSLContext,
) -> tuple[int, str]:
    request = Request(url, data=data, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout_sec, context=ssl_context) as response:
            return response.status, response.reason
    except HTTPError as error:
        return error.code, error.reason


def _load_session_from_envvar(
    cred_envvar: Literal[
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER",
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER",
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_METRICS_CREDENTIAL_PROVIDER",
    ],
):
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
        # `requests` is no longer a dependency of this package, so the
        # provider's return value can no longer be verified here.
        # from requests import Session
        # if isinstance(maybe_session, Session):
        #     return maybe_session
        # else:
        #     raise RuntimeError(
        #         f"Requested component '{_credential_env}' is of type {type(maybe_session)}"
        #         f" must be of type `Session`."
        #     )
        return maybe_session
    return None
