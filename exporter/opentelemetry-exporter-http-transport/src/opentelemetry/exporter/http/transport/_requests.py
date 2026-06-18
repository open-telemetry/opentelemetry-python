# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

# pylint: disable-next=import-error
from opentelemetry.exporter.http.transport._base import (
    BaseHTTPResult,
    BaseHTTPTransport,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

    import requests
    from requests import Response
    from typing_extensions import Self


@functools.cache
def _get_connection_error_types() -> tuple[type[Exception], ...]:
    # pylint: disable-next=import-outside-toplevel
    import requests.exceptions  # noqa: PLC0415

    return (
        requests.exceptions.ConnectionError,
        requests.exceptions.ConnectTimeout,
        requests.exceptions.ReadTimeout,
        requests.exceptions.Timeout,
        requests.exceptions.SSLError,
        requests.exceptions.ProxyError,
    )


@dataclass(frozen=True, slots=True)
class RequestsHTTPResult(BaseHTTPResult):
    response: Response | None = field(default=None, hash=False, compare=False)

    def content(self) -> bytes:
        if self.response is None:
            return b""
        return self.response.content or b""

    def text(self) -> str:
        if self.response is None:
            return ""
        return self.response.text or ""

    def json(self) -> Any:
        if self.response is None:
            raise ValueError("No response available.")
        return self.response.json()

    def headers(self) -> Mapping[str, str]:
        if self.response is None:
            return {}
        return self.response.headers


class RequestsHTTPTransport(BaseHTTPTransport):
    @classmethod
    def create(
        cls,
        verify: bool | str,
        cert: str | tuple[str, str] | None,
        **kwargs: Any,
    ) -> Self:
        return cls(verify=verify, cert=cert, **kwargs)

    def __init__(
        self,
        *,
        verify: bool | str = True,
        cert: str | tuple[str, str] | None = None,
        session: requests.Session | None = None,
    ) -> None:
        # pylint: disable-next=import-outside-toplevel
        import requests  # noqa: PLC0415

        self._session = session if session is not None else requests.Session()
        self._session.verify = verify
        if cert is not None:
            self._session.cert = cert

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        data: bytes | None = None,
    ) -> BaseHTTPResult:
        try:
            response = self._session.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                timeout=timeout,
                allow_redirects=False,
            )
        # pylint: disable-next=broad-exception-caught
        except Exception as error:
            # pylint: disable-next=unexpected-keyword-arg
            return RequestsHTTPResult(error=error)

        # pylint: disable-next=unexpected-keyword-arg
        return RequestsHTTPResult(
            status_code=response.status_code,
            reason=response.reason,
            response=response,
        )

    # pylint: disable-next=no-self-use
    def is_connection_error(self, exception: Exception | None) -> bool:
        return isinstance(exception, _get_connection_error_types())

    def close(self) -> None:
        self._session.close()
