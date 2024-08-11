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

RPC_CONNECT_RPC_ERROR_CODE: Final = "rpc.connect_rpc.error_code"
"""
The [error codes](https://connect.build/docs/protocol/#error-codes) of the Connect request. Error codes are always string values.
"""

RPC_CONNECT_RPC_REQUEST_METADATA_TEMPLATE: Final = (
    "rpc.connect_rpc.request.metadata"
)
"""
Connect request metadata, `<key>` being the normalized Connect Metadata key (lowercase), the value being the metadata values.
Note: Instrumentations SHOULD require an explicit configuration of which metadata values are to be captured. Including all request metadata values can be a security risk - explicit configuration helps avoid leaking sensitive information.
"""

RPC_CONNECT_RPC_RESPONSE_METADATA_TEMPLATE: Final = (
    "rpc.connect_rpc.response.metadata"
)
"""
Connect response metadata, `<key>` being the normalized Connect Metadata key (lowercase), the value being the metadata values.
Note: Instrumentations SHOULD require an explicit configuration of which metadata values are to be captured. Including all response metadata values can be a security risk - explicit configuration helps avoid leaking sensitive information.
"""

RPC_GRPC_REQUEST_METADATA_TEMPLATE: Final = "rpc.grpc.request.metadata"
"""
gRPC request metadata, `<key>` being the normalized gRPC Metadata key (lowercase), the value being the metadata values.
Note: Instrumentations SHOULD require an explicit configuration of which metadata values are to be captured. Including all request metadata values can be a security risk - explicit configuration helps avoid leaking sensitive information.
"""

RPC_GRPC_RESPONSE_METADATA_TEMPLATE: Final = "rpc.grpc.response.metadata"
"""
gRPC response metadata, `<key>` being the normalized gRPC Metadata key (lowercase), the value being the metadata values.
Note: Instrumentations SHOULD require an explicit configuration of which metadata values are to be captured. Including all response metadata values can be a security risk - explicit configuration helps avoid leaking sensitive information.
"""

RPC_GRPC_STATUS_CODE: Final = "rpc.grpc.status_code"
"""
The [numeric status code](https://github.com/grpc/grpc/blob/v1.33.2/doc/statuscodes.md) of the gRPC request.
"""

RPC_JSONRPC_ERROR_CODE: Final = "rpc.jsonrpc.error_code"
"""
`error.code` property of response if it is an error response.
"""

RPC_JSONRPC_ERROR_MESSAGE: Final = "rpc.jsonrpc.error_message"
"""
`error.message` property of response if it is an error response.
"""

RPC_JSONRPC_REQUEST_ID: Final = "rpc.jsonrpc.request_id"
"""
`id` property of request or response. Since protocol allows id to be int, string, `null` or missing (for notifications), value is expected to be cast to string for simplicity. Use empty string in case of `null` value. Omit entirely if this is a notification.
"""

RPC_JSONRPC_VERSION: Final = "rpc.jsonrpc.version"
"""
Protocol version as in `jsonrpc` property of request/response. Since JSON-RPC 1.0 doesn't specify this, the value can be omitted.
"""

RPC_METHOD: Final = "rpc.method"
"""
The name of the (logical) method being called, must be equal to the $method part in the span name.
Note: This is the logical name of the method from the RPC interface perspective, which can be different from the name of any implementing method/function. The `code.function` attribute may be used to store the latter (e.g., method actually executing the call on the server side, RPC client stub method on the client side).
"""

RPC_SERVICE: Final = "rpc.service"
"""
The full (logical) name of the service being called, including its package name, if applicable.
Note: This is the logical name of the service from the RPC interface perspective, which can be different from the name of any implementing class. The `code.namespace` attribute may be used to store the latter (despite the attribute name, it may include a class name; e.g., class with method actually executing the call on the server side, RPC client stub class on the client side).
"""

RPC_SYSTEM: Final = "rpc.system"
"""
A string identifying the remoting system. See below for a list of well-known identifiers.
"""


class RpcConnectRpcErrorCodeValues(Enum):
    CANCELLED: Final = "cancelled"
    """cancelled."""
    UNKNOWN: Final = "unknown"
    """unknown."""
    INVALID_ARGUMENT: Final = "invalid_argument"
    """invalid_argument."""
    DEADLINE_EXCEEDED: Final = "deadline_exceeded"
    """deadline_exceeded."""
    NOT_FOUND: Final = "not_found"
    """not_found."""
    ALREADY_EXISTS: Final = "already_exists"
    """already_exists."""
    PERMISSION_DENIED: Final = "permission_denied"
    """permission_denied."""
    RESOURCE_EXHAUSTED: Final = "resource_exhausted"
    """resource_exhausted."""
    FAILED_PRECONDITION: Final = "failed_precondition"
    """failed_precondition."""
    ABORTED: Final = "aborted"
    """aborted."""
    OUT_OF_RANGE: Final = "out_of_range"
    """out_of_range."""
    UNIMPLEMENTED: Final = "unimplemented"
    """unimplemented."""
    INTERNAL: Final = "internal"
    """internal."""
    UNAVAILABLE: Final = "unavailable"
    """unavailable."""
    DATA_LOSS: Final = "data_loss"
    """data_loss."""
    UNAUTHENTICATED: Final = "unauthenticated"
    """unauthenticated."""


class RpcGrpcStatusCodeValues(Enum):
    OK: Final = 0
    """OK."""
    CANCELLED: Final = 1
    """CANCELLED."""
    UNKNOWN: Final = 2
    """UNKNOWN."""
    INVALID_ARGUMENT: Final = 3
    """INVALID_ARGUMENT."""
    DEADLINE_EXCEEDED: Final = 4
    """DEADLINE_EXCEEDED."""
    NOT_FOUND: Final = 5
    """NOT_FOUND."""
    ALREADY_EXISTS: Final = 6
    """ALREADY_EXISTS."""
    PERMISSION_DENIED: Final = 7
    """PERMISSION_DENIED."""
    RESOURCE_EXHAUSTED: Final = 8
    """RESOURCE_EXHAUSTED."""
    FAILED_PRECONDITION: Final = 9
    """FAILED_PRECONDITION."""
    ABORTED: Final = 10
    """ABORTED."""
    OUT_OF_RANGE: Final = 11
    """OUT_OF_RANGE."""
    UNIMPLEMENTED: Final = 12
    """UNIMPLEMENTED."""
    INTERNAL: Final = 13
    """INTERNAL."""
    UNAVAILABLE: Final = 14
    """UNAVAILABLE."""
    DATA_LOSS: Final = 15
    """DATA_LOSS."""
    UNAUTHENTICATED: Final = 16
    """UNAUTHENTICATED."""


class RpcSystemValues(Enum):
    GRPC: Final = "grpc"
    """gRPC."""
    JAVA_RMI: Final = "java_rmi"
    """Java RMI."""
    DOTNET_WCF: Final = "dotnet_wcf"
    """.NET WCF."""
    APACHE_DUBBO: Final = "apache_dubbo"
    """Apache Dubbo."""
    CONNECT_RPC: Final = "connect_rpc"
    """Connect RPC."""
