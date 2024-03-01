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

# pylint: disable=too-many-lines

from enum import Enum


HTTP_CONNECTION_STATE = "http.connection.state"
"""
State of the HTTP connection in the HTTP connection pool.
"""


HTTP_FLAVOR = "http.flavor"
"""
Deprecated, use `network.protocol.name` instead.
Deprecated: Replaced by `network.protocol.name`.
"""


HTTP_METHOD = "http.method"
"""
Deprecated, use `http.request.method` instead.
Deprecated: Replaced by `http.request.method`.
"""


HTTP_REQUEST_BODY_SIZE = "http.request.body.size"
"""
The size of the request payload body in bytes. This is the number of bytes transferred excluding headers and is often, but not always, present as the [Content-Length](https://www.rfc-editor.org/rfc/rfc9110.html#field.content-length) header. For requests using transport encoding, this should be the compressed size.
"""


HTTP_REQUEST_CONTENT_LENGTH = "http.request_content_length"
"""
Deprecated, use `http.request.header.content-length` instead.
Deprecated: Replaced by `http.request.header.content-length`.
"""


HTTP_RESPONSE_BODY_SIZE = "http.response.body.size"
"""
The size of the response payload body in bytes. This is the number of bytes transferred excluding headers and is often, but not always, present as the [Content-Length](https://www.rfc-editor.org/rfc/rfc9110.html#field.content-length) header. For requests using transport encoding, this should be the compressed size.
"""


HTTP_RESPONSE_CONTENT_LENGTH = "http.response_content_length"
"""
Deprecated, use `http.response.header.content-length` instead.
Deprecated: Replaced by `http.response.header.content-length`.
"""


HTTP_SCHEME = "http.scheme"
"""
Deprecated, use `url.scheme` instead.
Deprecated: Replaced by `url.scheme` instead.
"""


HTTP_STATUS_CODE = "http.status_code"
"""
Deprecated, use `http.response.status_code` instead.
Deprecated: Replaced by `http.response.status_code`.
"""


HTTP_TARGET = "http.target"
"""
Deprecated, use `url.path` and `url.query` instead.
Deprecated: Split to `url.path` and `url.query.
"""


HTTP_URL = "http.url"
"""
Deprecated, use `url.full` instead.
Deprecated: Replaced by `url.full`.
"""


HTTP_USER_AGENT = "http.user_agent"
"""
Deprecated, use `user_agent.original` instead.
Deprecated: Replaced by `user_agent.original`.
"""

class HttpConnectionStateValues(Enum):
    ACTIVE = "active"
    """active state."""

    IDLE = "idle"
    """idle state."""
class HttpFlavorValues(Enum):
    HTTP_1_0 = "1.0"
    """HTTP/1.0."""

    HTTP_1_1 = "1.1"
    """HTTP/1.1."""

    HTTP_2_0 = "2.0"
    """HTTP/2."""

    HTTP_3_0 = "3.0"
    """HTTP/3."""

    SPDY = "SPDY"
    """SPDY protocol."""

    QUIC = "QUIC"
    """QUIC protocol."""
