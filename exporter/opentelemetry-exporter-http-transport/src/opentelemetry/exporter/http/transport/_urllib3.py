# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import functools
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

# pylint: disable-next=import-error
from opentelemetry.exporter.http.transport._base import (
    BaseHTTPResult,
    BaseHTTPTransport,
)

# pylint: disable-next=import-error
from opentelemetry.exporter.http.transport._proxy import (
    _get_environ_proxy,
    _get_proxy_auth,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

    from urllib3 import BaseHTTPResponse, PoolManager


@functools.cache
def _get_connection_error_types() -> tuple[type[Exception], ...]:
    # pylint: disable-next=import-outside-toplevel
    import urllib3.exceptions  # noqa: PLC0415

    types: list[type[Exception]] = [
        urllib3.exceptions.ConnectionError,
        urllib3.exceptions.NewConnectionError,
        urllib3.exceptions.ConnectTimeoutError,
        urllib3.exceptions.MaxRetryError,
        urllib3.exceptions.ProtocolError,
        urllib3.exceptions.ProxyError,
        urllib3.exceptions.ReadTimeoutError,
    ]

    # NameResolutionError was added in urllib3 2.0
    name_resolution_error = getattr(urllib3.exceptions, "NameResolutionError", None)
    if name_resolution_error is not None:
        types.append(name_resolution_error)

    return tuple(types)


@dataclass(frozen=True, slots=True)
class Urllib3HTTPResult(BaseHTTPResult):
    response: BaseHTTPResponse | None = field(default=None, hash=False, compare=False)

    def content(self) -> bytes:
        if self.response is None:
            return b""
        return self.response.data or b""

    def headers(self) -> Mapping[str, str]:
        if self.response is None:
            return {}
        return self.response.headers

    def json(self) -> Any:
        if self.response is None:
            raise ValueError("No response available.")
        return json.loads(self.content())


class Urllib3HTTPTransport(BaseHTTPTransport):
    def __init__(
        self,
        *,
        verify: bool | str = True,
        cert: str | tuple[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        # pylint: disable-next=import-outside-toplevel
        import urllib3  # noqa: PLC0415

        pool_kwargs: dict[str, Any] = {
            "retries": urllib3.Retry(0, redirect=False),
            # Match the connection pool size of requests
            "maxsize": 10,
        }
        if verify is False:
            pool_kwargs["cert_reqs"] = "CERT_NONE"
        else:
            pool_kwargs["cert_reqs"] = "CERT_REQUIRED"
            if isinstance(verify, str):
                pool_kwargs["ca_certs"] = verify
            else:
                # Prefer certifi's CA bundle, as requests does, falling back
                # to the system trust store when certifi is not installed.
                try:
                    # pylint: disable-next=import-outside-toplevel
                    import certifi  # noqa: PLC0415
                except ImportError:
                    pass
                else:
                    pool_kwargs["ca_certs"] = certifi.where()
        if isinstance(cert, tuple):
            pool_kwargs["cert_file"] = cert[0]
            pool_kwargs["key_file"] = cert[1]
        elif isinstance(cert, str):
            pool_kwargs["cert_file"] = cert

        self._pool_kwargs = pool_kwargs
        self._pool = urllib3.PoolManager(**pool_kwargs)  # type: ignore
        self._proxy_managers: dict[str, PoolManager] = {}
        self._get_proxy = functools.lru_cache(maxsize=32)(_get_environ_proxy)

    def _get_pool_manager(self, url: str) -> PoolManager:
        proxy = self._get_proxy(url)
        if proxy is None:
            return self._pool
        manager = self._proxy_managers.get(proxy)
        if manager is None:
            manager = self._proxy_managers.setdefault(proxy, self._new_proxy_manager(proxy))
        return manager

    def _new_proxy_manager(self, proxy: str) -> PoolManager:
        # pylint: disable-next=import-outside-toplevel
        import urllib3  # noqa: PLC0415

        username, password = _get_proxy_auth(proxy)
        if proxy.lower().startswith("socks"):
            try:
                # pylint: disable-next=import-outside-toplevel
                from urllib3.contrib.socks import (  # noqa: PLC0415
                    SOCKSProxyManager,
                )
            except ImportError as error:
                raise ImportError(
                    "SOCKS proxy support requires PySocks, install it with 'pip install urllib3[socks]'."
                ) from error
            return SOCKSProxyManager(
                proxy,
                username=username,
                password=password,
                **self._pool_kwargs,
            )
        proxy_headers = urllib3.make_headers(proxy_basic_auth=f"{username}:{password}") if username else None
        return urllib3.proxy_from_url(
            proxy,
            proxy_headers=proxy_headers,
            **self._pool_kwargs,
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        data: bytes | None = None,
    ) -> BaseHTTPResult:
        # pylint: disable-next=import-outside-toplevel
        import urllib3  # noqa: PLC0415

        try:
            response = self._get_pool_manager(url).request(
                method=method,
                url=url,
                headers=headers,
                body=data,
                timeout=urllib3.Timeout(total=timeout) if timeout is not None else None,
                preload_content=True,
            )
        # pylint: disable-next=broad-exception-caught
        except Exception as error:
            # pylint: disable-next=unexpected-keyword-arg
            return Urllib3HTTPResult(error=error)

        # pylint: disable-next=unexpected-keyword-arg
        return Urllib3HTTPResult(
            status_code=response.status,
            reason=response.reason,
            response=response,
        )

    # pylint: disable-next=no-self-use
    def is_connection_error(self, exception: Exception | None) -> bool:
        return isinstance(exception, _get_connection_error_types())

    def close(self) -> None:
        self._pool.clear()
        for manager in self._proxy_managers.values():
            manager.clear()
        self._proxy_managers.clear()
        self._get_proxy.cache_clear()
