# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import ssl
from os import environ
from typing import Callable, Literal
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPSHandler,
    OpenerDirector,
    Request,
    build_opener,
)
from warnings import warn

from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER,
)
from opentelemetry.util._importlib_metadata import entry_points

# A client sends one already-serialized, already-compressed payload and reports
# back the HTTP status code and reason phrase. Transport-level failures are
# raised as URLError so the exporters' retry loops treat them as retryable.
_Client = Callable[[str, bytes, "dict[str, str]", float], "tuple[int, str]"]

_CREDENTIAL_PROVIDER_ENTRY_POINT = "opentelemetry_otlp_credential_provider"

_DEPRECATED_SESSION_MESSAGE = (
    "Passing a requests.Session (or any object exposing a .post() method) to the "
    "OTLP HTTP exporter - through the `session` argument, or via a "
    "'opentelemetry_otlp_credential_provider' entry point named by "
    "OTEL_PYTHON_EXPORTER_OTLP_HTTP[_TRACES|_METRICS|_LOGS]_CREDENTIAL_PROVIDER - "
    "is deprecated and will be removed in a future release. Return a "
    "urllib.request.OpenerDirector instead."
)


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


def _opener_client(opener: OpenerDirector) -> _Client:
    def post(url, data, headers, timeout_sec):
        request = Request(url, data=data, headers=headers, method="POST")
        try:
            with opener.open(request, timeout=timeout_sec) as response:
                return response.status, response.reason
        except HTTPError as error:
            return error.code, error.reason

    return post


def _session_client(session: object) -> _Client:
    def post(url, data, headers, timeout_sec):
        try:
            response = session.post(
                url, data=data, headers=headers, timeout=timeout_sec
            )
        except OSError as error:
            # requests' transport exceptions subclass OSError; surface them as a
            # URLError so the exporters' retry loops handle them uniformly.
            raise URLError(error) from error
        return response.status_code, response.reason

    return post


def _load_provider_from_envvar(
    cred_envvar: Literal[
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER",
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER",
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_METRICS_CREDENTIAL_PROVIDER",
    ],
) -> object | None:
    name = environ.get(
        _OTEL_PYTHON_EXPORTER_OTLP_HTTP_CREDENTIAL_PROVIDER
    ) or environ.get(cred_envvar)
    if not name:
        return None
    try:
        provider = next(
            iter(entry_points(group=_CREDENTIAL_PROVIDER_ENTRY_POINT, name=name))
        )
    except StopIteration:
        raise RuntimeError(
            f"Requested component '{name}' not found in entry point "
            f"'{_CREDENTIAL_PROVIDER_ENTRY_POINT}'"
        )
    return provider.load()()


def _resolve_client(
    session: object | None,
    cred_envvar: Literal[
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER",
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER",
        "OTEL_PYTHON_EXPORTER_OTLP_HTTP_METRICS_CREDENTIAL_PROVIDER",
    ],
    ssl_context: ssl.SSLContext,
) -> _Client:
    """Resolve the HTTP client the exporter sends through.

    Precedence mirrors the original ``requests``-based exporter: an explicit
    ``session`` argument wins, otherwise the object produced by the credential
    provider named in the environment, otherwise a default stdlib opener built
    from ``ssl_context``.

    A ``urllib.request.OpenerDirector`` is the supported injectable. A
    ``requests.Session`` (detected structurally, without importing ``requests``)
    is still accepted for backwards compatibility but is deprecated.
    """
    injectable = (
        session
        if session is not None
        else _load_provider_from_envvar(cred_envvar)
    )
    if injectable is None:
        return _opener_client(build_opener(HTTPSHandler(context=ssl_context)))
    if isinstance(injectable, OpenerDirector):
        return _opener_client(injectable)
    if callable(getattr(injectable, "post", None)):
        warn(_DEPRECATED_SESSION_MESSAGE, DeprecationWarning, stacklevel=2)
        return _session_client(injectable)
    raise RuntimeError(
        "OTLP HTTP credential provider must return a "
        "urllib.request.OpenerDirector (or, deprecated, a requests.Session); "
        f"got {type(injectable)}"
    )
