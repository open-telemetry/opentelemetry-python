# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import functools
import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING

from opentelemetry.exporter.http.transport._base import (
    BaseHTTPResult,
    BaseHTTPTransport,
)

if TYPE_CHECKING:
    import requests


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
    def is_connection_error(self) -> bool:
        if self.error is None:
            return False
        return isinstance(self.error, _get_connection_error_types())


class RequestsHTTPTransport(BaseHTTPTransport):
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

        if verify is False:
            # pylint: disable-next=import-outside-toplevel
            from urllib3.exceptions import (  # noqa: PLC0415
                InsecureRequestWarning,
            )

            warnings.filterwarnings("ignore", category=InsecureRequestWarning)

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
            return RequestsHTTPResult(error=error)

        return RequestsHTTPResult(
            status_code=response.status_code,
            reason=response.reason,
        )

    def close(self) -> None:
        self._session.close()
