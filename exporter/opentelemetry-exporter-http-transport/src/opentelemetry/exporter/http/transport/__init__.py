# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from opentelemetry.exporter.http.transport._base import BaseHTTPTransport


def _load_requests_transport() -> type[BaseHTTPTransport]:
    # pylint: disable-next=import-outside-toplevel,import-error
    from opentelemetry.exporter.http.transport._requests import (  # noqa: PLC0415
        RequestsHTTPTransport,
    )

    return RequestsHTTPTransport


def _load_urllib3_transport() -> type[BaseHTTPTransport]:
    # pylint: disable-next=import-outside-toplevel,import-error
    from opentelemetry.exporter.http.transport._urllib3 import (  # noqa: PLC0415
        Urllib3HTTPTransport,
    )

    return Urllib3HTTPTransport


_KNOWN_TRANSPORTS: dict[str, Callable[[], type[BaseHTTPTransport]]] = {
    "requests": _load_requests_transport,
    "urllib3": _load_urllib3_transport,
}


def _load_http_transport_class(name: str) -> type[BaseHTTPTransport]:
    """Return the transport class registered under *name*.

    Checks the built-in transport registry first to avoid the overhead of an
    entry-point scan for built-in transports. Falls back to standard entry-point
    discovery for user supplied transports registered under the
    ``opentelemetry_http_transport`` group.

    :param name: Entry point name, e.g. ``"requests"`` or ``"urllib3"``.
    :returns: The :class:`~opentelemetry.exporter.http.transport._base.BaseHTTPTransport`
        subclass registered under *name*.
    :raises ValueError: If no transport is registered under *name*.
    """
    if name in _KNOWN_TRANSPORTS:
        return _KNOWN_TRANSPORTS[name]()
    # pylint: disable-next=import-outside-toplevel,import-error
    from opentelemetry.util._importlib_metadata import (  # noqa: PLC0415
        entry_points,
    )

    ep = next(
        iter(entry_points(group="opentelemetry_http_transport", name=name)),
        None,
    )
    if not ep:
        raise ValueError(
            f"No HTTP transport registered under name {name!r}. "
            "Install the corresponding extra or register an entry point "
            "under the 'opentelemetry_http_transport' group."
        )
    return ep.load()
