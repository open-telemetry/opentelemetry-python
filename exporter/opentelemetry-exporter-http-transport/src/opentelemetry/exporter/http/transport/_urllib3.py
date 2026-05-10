# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import functools
import warnings
from dataclasses import dataclass

from opentelemetry.exporter.http.transport._base import (
    BaseHTTPResult,
    BaseHTTPTransport,
)


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
    ]

    # NameResolutionError was added in urllib3 2.0
    name_resolution_error = getattr(
        urllib3.exceptions, "NameResolutionError", None
    )
    if name_resolution_error is not None:
        types.append(name_resolution_error)

    return tuple(types)


@dataclass(frozen=True, slots=True)
class Urllib3HTTPResult(BaseHTTPResult):
    def is_connection_error(self) -> bool:
        if self.error is None:
            return False
        return isinstance(self.error, _get_connection_error_types())


class Urllib3HTTPTransport(BaseHTTPTransport):
    def __init__(
        self,
        *,
        verify: bool | str = True,
        cert: str | tuple[str, str] | None = None,
    ) -> None:
        # pylint: disable-next=import-outside-toplevel
        import urllib3  # noqa: PLC0415

        pool_kwargs: dict[str, object] = {
            "retries": urllib3.Retry(0, redirect=False),
        }
        if verify is False:
            pool_kwargs["cert_reqs"] = "CERT_NONE"
            warnings.filterwarnings(
                "ignore",
                category=urllib3.exceptions.InsecureRequestWarning,
            )
        else:
            pool_kwargs["cert_reqs"] = "CERT_REQUIRED"
            if isinstance(verify, str):
                pool_kwargs["ca_certs"] = verify
        if isinstance(cert, tuple):
            pool_kwargs["cert_file"] = cert[0]
            pool_kwargs["key_file"] = cert[1]
        elif isinstance(cert, str):
            pool_kwargs["cert_file"] = cert

        self._pool = urllib3.PoolManager(**pool_kwargs)  # type: ignore

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
            response = self._pool.request(
                method=method,
                url=url,
                headers=headers,
                body=data,
                timeout=urllib3.Timeout(total=timeout)
                if timeout is not None
                else None,
                preload_content=True,
            )
        # pylint: disable-next=broad-exception-caught
        except Exception as error:
            return Urllib3HTTPResult(error=error)

        return Urllib3HTTPResult(
            status_code=response.status,
            reason=response.reason,
        )

    def close(self) -> None:
        self._pool.clear()
