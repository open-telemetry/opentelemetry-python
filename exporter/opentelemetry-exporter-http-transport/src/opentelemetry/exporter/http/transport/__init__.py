# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING, cast

# pylint: disable-next=import-error
from opentelemetry.exporter.http.transport._requests import (
    RequestsHTTPTransport as _RequestsHTTPTransport,
)

# pylint: disable-next=import-error
from opentelemetry.exporter.http.transport._urllib3 import (
    Urllib3HTTPTransport as _Urllib3HTTPTransport,
)

if TYPE_CHECKING:
    from typing import Any, Protocol

    from opentelemetry.exporter.http.transport._base import BaseHTTPTransport

    class BaseHTTPTransportFactory(Protocol):
        def __call__(
            self,
            *,
            verify: bool | str,
            cert: str | tuple[str, str] | None,
            **kwargs: Any,
        ) -> BaseHTTPTransport: ...


_KNOWN_TRANSPORTS: dict[str, BaseHTTPTransportFactory] = {
    "requests": _RequestsHTTPTransport,
    "urllib3": _Urllib3HTTPTransport,
}


def _load_http_transport_factory(name: str) -> BaseHTTPTransportFactory:
    """Return the transport factory registered under *name*.

    Checks the built-in transport registry first to avoid the overhead of an
    entry-point scan for built-in transports. Falls back to standard entry-point
    discovery for user supplied transports registered under the
    ``opentelemetry_http_transport`` group.

    :param name: Entry point name, e.g. ``"requests"`` or ``"urllib3"``.
    :returns: A callable with signature
        ``(*, verify, cert, **kwargs) -> BaseHTTPTransport``.
    :raises ValueError: If no transport is registered under *name*.
    :raises TypeError: If the loaded entry point is not callable.
    """
    if name in _KNOWN_TRANSPORTS:
        return _KNOWN_TRANSPORTS[name]
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
    factory = ep.load()
    if not callable(factory):
        raise TypeError(
            f"Transport {name!r} loaded from entry point is not callable "
            f"(got {factory!r})."
        )
    return cast("BaseHTTPTransportFactory", factory)
