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

from typing import Final

JSONRPC_PROTOCOL_VERSION: Final = "jsonrpc.protocol.version"
"""
Protocol version, as specified in the `jsonrpc` property of the request and its corresponding response.
"""

JSONRPC_REQUEST_ID: Final = "jsonrpc.request.id"
"""
A string representation of the `id` property of the request and its corresponding response.
Note: Under the [JSON-RPC specification](https://www.jsonrpc.org/specification), the `id` property may be a string, number, null, or omitted entirely. When omitted, the request is treated as a notification. Using `null` is not equivalent to omitting the `id`, but it is discouraged.
Instrumentations SHOULD NOT capture this attribute when the `id` is `null` or omitted.
"""
