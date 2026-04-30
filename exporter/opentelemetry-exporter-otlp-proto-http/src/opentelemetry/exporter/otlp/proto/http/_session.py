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

import warnings
from typing import Protocol, runtime_checkable

import urllib3


@runtime_checkable
class HttpResponse(Protocol):
    status_code: int
    reason: str | None


@runtime_checkable
class HttpSession(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        data: bytes | None = None,
    ) -> HttpResponse: ...

    def close(self) -> None: ...


class _Urllib3Response:
    def __init__(self, resp: urllib3.HTTPResponse) -> None:
        self._resp = resp

    @property
    def status_code(self) -> int:
        return self._resp.status

    @property
    def reason(self) -> str | None:
        return self._resp.reason

class Urllib3Session:
    """Default :class:`HttpSession` implementation backed by ``urllib3``.

    ``verify`` follows the same semantics as ``requests``: ``True`` enables
    certificate verification against the system trust store, ``False``
    disables it, and a string is treated as a path to a CA bundle. ``cert``
    is either a path to a client certificate file, or a ``(cert, key)``
    tuple for mutual TLS.
    """

    def __init__(
        self,
        *,
        verify: bool | str = True,
        cert: str | tuple[str, str] | None = None,
    ) -> None:
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

        self._pool = urllib3.PoolManager(**pool_kwargs)

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        data: bytes | None = None,
    ) -> HttpResponse:
        resp = self._pool.request(
            method,
            url,
            body=data,
            headers=headers,
            timeout=timeout,
        )
        return _Urllib3Response(resp)

    def close(self) -> None:
        self._pool.clear()
