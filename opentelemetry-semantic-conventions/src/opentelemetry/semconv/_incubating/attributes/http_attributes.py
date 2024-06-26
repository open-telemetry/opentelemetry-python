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

from enum import Enum
from typing import Final

from deprecated import deprecated

HTTP_CLIENT_IP: Final = "http.client_ip"
"""
Deprecated: Replaced by `client.address`.
"""

HTTP_CONNECTION_STATE: Final = "http.connection.state"
"""
State of the HTTP connection in the HTTP connection pool.
"""

HTTP_FLAVOR: Final = "http.flavor"
"""
Deprecated: Replaced by `network.protocol.name`.
"""

HTTP_HOST: Final = "http.host"
"""
Deprecated: Replaced by one of `server.address`, `client.address` or `http.request.header.host`, depending on the usage.
"""

HTTP_METHOD: Final = "http.method"
"""
Deprecated: Replaced by `http.request.method`.
"""

HTTP_REQUEST_BODY_SIZE: Final = "http.request.body.size"
"""
The size of the request payload body in bytes. This is the number of bytes transferred excluding headers and is often, but not always, present as the [Content-Length](https://www.rfc-editor.org/rfc/rfc9110.html#field.content-length) header. For requests using transport encoding, this should be the compressed size.
"""

HTTP_REQUEST_HEADER_TEMPLATE: Final = "http.request.header"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.http_attributes.HTTP_REQUEST_HEADER_TEMPLATE`.
"""

HTTP_REQUEST_METHOD: Final = "http.request.method"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.http_attributes.HTTP_REQUEST_METHOD`.
"""

HTTP_REQUEST_METHOD_ORIGINAL: Final = "http.request.method_original"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.http_attributes.HTTP_REQUEST_METHOD_ORIGINAL`.
"""

HTTP_REQUEST_RESEND_COUNT: Final = "http.request.resend_count"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.http_attributes.HTTP_REQUEST_RESEND_COUNT`.
"""

HTTP_REQUEST_SIZE: Final = "http.request.size"
"""
The total size of the request in bytes. This should be the total number of bytes sent over the wire, including the request line (HTTP/1.1), framing (HTTP/2 and HTTP/3), headers, and request body if any.
"""

HTTP_REQUEST_CONTENT_LENGTH: Final = "http.request_content_length"
"""
Deprecated: Replaced by `http.request.header.content-length`.
"""

HTTP_REQUEST_CONTENT_LENGTH_UNCOMPRESSED: Final = (
    "http.request_content_length_uncompressed"
)
"""
Deprecated: Replaced by `http.request.body.size`.
"""

HTTP_RESPONSE_BODY_SIZE: Final = "http.response.body.size"
"""
The size of the response payload body in bytes. This is the number of bytes transferred excluding headers and is often, but not always, present as the [Content-Length](https://www.rfc-editor.org/rfc/rfc9110.html#field.content-length) header. For requests using transport encoding, this should be the compressed size.
"""

HTTP_RESPONSE_HEADER_TEMPLATE: Final = "http.response.header"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.http_attributes.HTTP_RESPONSE_HEADER_TEMPLATE`.
"""

HTTP_RESPONSE_SIZE: Final = "http.response.size"
"""
The total size of the response in bytes. This should be the total number of bytes sent over the wire, including the status line (HTTP/1.1), framing (HTTP/2 and HTTP/3), headers, and response body and trailers if any.
"""

HTTP_RESPONSE_STATUS_CODE: Final = "http.response.status_code"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.http_attributes.HTTP_RESPONSE_STATUS_CODE`.
"""

HTTP_RESPONSE_CONTENT_LENGTH: Final = "http.response_content_length"
"""
Deprecated: Replaced by `http.response.header.content-length`.
"""

HTTP_RESPONSE_CONTENT_LENGTH_UNCOMPRESSED: Final = (
    "http.response_content_length_uncompressed"
)
"""
Deprecated: Replace by `http.response.body.size`.
"""

HTTP_ROUTE: Final = "http.route"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.http_attributes.HTTP_ROUTE`.
"""

HTTP_SCHEME: Final = "http.scheme"
"""
Deprecated: Replaced by `url.scheme` instead.
"""

HTTP_SERVER_NAME: Final = "http.server_name"
"""
Deprecated: Replaced by `server.address`.
"""

HTTP_STATUS_CODE: Final = "http.status_code"
"""
Deprecated: Replaced by `http.response.status_code`.
"""

HTTP_TARGET: Final = "http.target"
"""
Deprecated: Split to `url.path` and `url.query.
"""

HTTP_URL: Final = "http.url"
"""
Deprecated: Replaced by `url.full`.
"""

HTTP_USER_AGENT: Final = "http.user_agent"
"""
Deprecated: Replaced by `user_agent.original`.
"""


class HttpConnectionStateValues(Enum):
    ACTIVE: Final = "active"
    """active state."""
    IDLE: Final = "idle"
    """idle state."""


@deprecated(reason="The attribute http.flavor is deprecated - Replaced by `network.protocol.name`")  # type: ignore
class HttpFlavorValues(Enum):
    HTTP_1_0: Final = "1.0"
    """HTTP/1.0."""
    HTTP_1_1: Final = "1.1"
    """HTTP/1.1."""
    HTTP_2_0: Final = "2.0"
    """HTTP/2."""
    HTTP_3_0: Final = "3.0"
    """HTTP/3."""
    SPDY: Final = "SPDY"
    """SPDY protocol."""
    QUIC: Final = "QUIC"
    """QUIC protocol."""


@deprecated(reason="Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.http_attributes.HttpRequestMethodValues`.")  # type: ignore
class HttpRequestMethodValues(Enum):
    CONNECT: Final = "CONNECT"
    """CONNECT method."""
    DELETE: Final = "DELETE"
    """DELETE method."""
    GET: Final = "GET"
    """GET method."""
    HEAD: Final = "HEAD"
    """HEAD method."""
    OPTIONS: Final = "OPTIONS"
    """OPTIONS method."""
    PATCH: Final = "PATCH"
    """PATCH method."""
    POST: Final = "POST"
    """POST method."""
    PUT: Final = "PUT"
    """PUT method."""
    TRACE: Final = "TRACE"
    """TRACE method."""
    OTHER: Final = "_OTHER"
    """Any HTTP method that the instrumentation has no prior knowledge of."""
