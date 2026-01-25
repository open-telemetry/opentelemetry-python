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

"""
Internal HTTP client using stdlib http.client with connection pooling and SSL support.
"""

import http.client
import ssl
import threading
from dataclasses import dataclass
from typing import Dict, Optional, Union
from urllib.parse import urlparse


@dataclass
class HttpResponse:
    """Simple response object mimicking the subset of requests.Response we use."""

    status_code: int
    reason: str
    text: str

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


class HttpClient:
    """
    HTTP client with connection pooling and SSL support.

    Uses http.client for persistent connections (keep-alive).
    Thread-safe through connection-per-thread approach.
    """

    def __init__(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        certificate_file: Optional[Union[str, bool]] = None,
        client_key_file: Optional[str] = None,
        client_certificate_file: Optional[str] = None,
    ):
        parsed = urlparse(endpoint)
        self._scheme = parsed.scheme
        self._host = parsed.hostname or "localhost"
        self._port = parsed.port or (443 if self._scheme == "https" else 80)
        self._path = parsed.path or "/"
        if parsed.query:
            self._path += f"?{parsed.query}"

        self._headers = headers or {}
        self._timeout = timeout

        # Store SSL params for deferred context creation
        self._certificate_file = certificate_file
        self._client_key_file = client_key_file
        self._client_certificate_file = client_certificate_file
        self._ssl_context: Optional[ssl.SSLContext] = None
        self._ssl_context_initialized = False

        # Thread-local storage for connections (one connection per thread)
        self._local = threading.local()
        self._closed = False

    def _create_ssl_context(
        self,
        certificate_file: Optional[Union[str, bool]],
        client_key_file: Optional[str],
        client_certificate_file: Optional[str],
    ) -> Optional[ssl.SSLContext]:
        """Create SSL context for HTTPS connections."""
        if self._scheme != "https":
            return None

        # Create context with secure defaults
        context = ssl.create_default_context()

        # Handle CA certificate verification
        if certificate_file is False:
            # Disable verification (not recommended for production)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        elif isinstance(certificate_file, str):
            # Load custom CA certificate
            context.load_verify_locations(cafile=certificate_file)
        # If True or None, use system default CA certificates (already configured)

        # Load client certificate if provided
        if client_certificate_file:
            context.load_cert_chain(
                certfile=client_certificate_file,
                keyfile=client_key_file,
            )

        return context

    def _get_connection(self) -> Union[http.client.HTTPConnection, http.client.HTTPSConnection]:
        """Get or create a connection for the current thread."""
        conn = getattr(self._local, "connection", None)

        # Check if we need a new connection
        if conn is None:
            conn = self._create_connection()
            self._local.connection = conn

        return conn

    def _get_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Get or create the SSL context (lazy initialization)."""
        if not self._ssl_context_initialized:
            self._ssl_context = self._create_ssl_context(
                self._certificate_file,
                self._client_key_file,
                self._client_certificate_file,
            )
            self._ssl_context_initialized = True
        return self._ssl_context

    def _create_connection(self) -> Union[http.client.HTTPConnection, http.client.HTTPSConnection]:
        """Create a new HTTP(S) connection."""
        if self._scheme == "https":
            return http.client.HTTPSConnection(
                self._host,
                self._port,
                timeout=self._timeout,
                context=self._get_ssl_context(),
            )
        else:
            return http.client.HTTPConnection(
                self._host,
                self._port,
                timeout=self._timeout,
            )

    def _reset_connection(self) -> None:
        """Close and remove the current thread's connection."""
        conn = getattr(self._local, "connection", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.connection = None

    def post(self, data: bytes, timeout: Optional[float] = None) -> HttpResponse:
        """
        Send a POST request with the given data.

        Handles connection errors by retrying once with a fresh connection.
        """
        if self._closed:
            raise RuntimeError("HttpClient has been closed")

        # Try to send the request, retry once on connection error
        for attempt in range(2):
            try:
                return self._do_post(data, timeout)
            except (http.client.HTTPException, OSError, ConnectionError) as e:
                # On first attempt, reset connection and retry
                if attempt == 0:
                    self._reset_connection()
                    continue
                # On second attempt, raise the error
                raise

        # This should never be reached, but just in case
        raise RuntimeError("Failed to send request")

    def _do_post(self, data: bytes, timeout: Optional[float] = None) -> HttpResponse:
        """Internal method to perform the actual POST request."""
        conn = self._get_connection()

        # Update timeout if specified for this request
        if timeout is not None:
            conn.timeout = timeout
        elif self._timeout is not None:
            conn.timeout = self._timeout

        # Send the request
        conn.request(
            "POST",
            self._path,
            body=data,
            headers=self._headers,
        )

        # Get the response
        response = conn.getresponse()

        # Read the response body
        body = response.read()
        text = body.decode("utf-8", errors="replace")

        return HttpResponse(
            status_code=response.status,
            reason=response.reason,
            text=text,
        )

    def close(self) -> None:
        """Close the client and all connections."""
        self._closed = True
        self._reset_connection()
