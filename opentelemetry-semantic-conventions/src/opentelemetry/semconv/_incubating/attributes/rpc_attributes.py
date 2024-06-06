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

RPC_CONNECTRPC_ERRORCODE = "rpc.connect_rpc.error_code"
"""
The [error codes](https://connect.build/docs/protocol/#error-codes) of the Connect request. Error codes are always string values.
"""

RPC_CONNECTRPC_REQUEST_METADATA_TEMPLATE = "rpc.connect_rpc.request.metadata"
"""
Connect request metadata, `<key>` being the normalized Connect Metadata key (lowercase), the value being the metadata values.
Note: Instrumentations SHOULD require an explicit configuration of which metadata values are to be captured. Including all request metadata values can be a security risk - explicit configuration helps avoid leaking sensitive information.
"""

RPC_CONNECTRPC_RESPONSE_METADATA_TEMPLATE = "rpc.connect_rpc.response.metadata"
"""
Connect response metadata, `<key>` being the normalized Connect Metadata key (lowercase), the value being the metadata values.
Note: Instrumentations SHOULD require an explicit configuration of which metadata values are to be captured. Including all response metadata values can be a security risk - explicit configuration helps avoid leaking sensitive information.
"""

RPC_GRPC_REQUEST_METADATA_TEMPLATE = "rpc.grpc.request.metadata"
"""
gRPC request metadata, `<key>` being the normalized gRPC Metadata key (lowercase), the value being the metadata values.
Note: Instrumentations SHOULD require an explicit configuration of which metadata values are to be captured. Including all request metadata values can be a security risk - explicit configuration helps avoid leaking sensitive information.
"""

RPC_GRPC_RESPONSE_METADATA_TEMPLATE = "rpc.grpc.response.metadata"
"""
gRPC response metadata, `<key>` being the normalized gRPC Metadata key (lowercase), the value being the metadata values.
Note: Instrumentations SHOULD require an explicit configuration of which metadata values are to be captured. Including all response metadata values can be a security risk - explicit configuration helps avoid leaking sensitive information.
"""

RPC_GRPC_STATUSCODE = "rpc.grpc.status_code"
"""
The [numeric status code](https://github.com/grpc/grpc/blob/v1.33.2/doc/statuscodes.md) of the gRPC request.
"""

RPC_JSONRPC_ERRORCODE = "rpc.jsonrpc.error_code"
"""
`error.code` property of response if it is an error response.
"""

RPC_JSONRPC_ERRORMESSAGE = "rpc.jsonrpc.error_message"
"""
`error.message` property of response if it is an error response.
"""

RPC_JSONRPC_REQUESTID = "rpc.jsonrpc.request_id"
"""
`id` property of request or response. Since protocol allows id to be int, string, `null` or missing (for notifications), value is expected to be cast to string for simplicity. Use empty string in case of `null` value. Omit entirely if this is a notification.
"""

RPC_JSONRPC_VERSION = "rpc.jsonrpc.version"
"""
Protocol version as in `jsonrpc` property of request/response. Since JSON-RPC 1.0 doesn't specify this, the value can be omitted.
"""

RPC_METHOD = "rpc.method"
"""
The name of the (logical) method being called, must be equal to the $method part in the span name.
Note: This is the logical name of the method from the RPC interface perspective, which can be different from the name of any implementing method/function. The `code.function` attribute may be used to store the latter (e.g., method actually executing the call on the server side, RPC client stub method on the client side).
"""

RPC_SERVICE = "rpc.service"
"""
The full (logical) name of the service being called, including its package name, if applicable.
Note: This is the logical name of the service from the RPC interface perspective, which can be different from the name of any implementing class. The `code.namespace` attribute may be used to store the latter (despite the attribute name, it may include a class name; e.g., class with method actually executing the call on the server side, RPC client stub class on the client side).
"""

RPC_SYSTEM = "rpc.system"
"""
A string identifying the remoting system. See below for a list of well-known identifiers.
"""


class RpcConnectrpcErrorcodeValues(Enum):
    CANCELLED = "cancelled"
    """cancelled."""
    UNKNOWN = "unknown"
    """unknown."""
    INVALIDARGUMENT = "invalid_argument"
    """invalid_argument."""
    DEADLINEEXCEEDED = "deadline_exceeded"
    """deadline_exceeded."""
    NOTFOUND = "not_found"
    """not_found."""
    ALREADYEXISTS = "already_exists"
    """already_exists."""
    PERMISSIONDENIED = "permission_denied"
    """permission_denied."""
    RESOURCEEXHAUSTED = "resource_exhausted"
    """resource_exhausted."""
    FAILEDPRECONDITION = "failed_precondition"
    """failed_precondition."""
    ABORTED = "aborted"
    """aborted."""
    OUTOFRANGE = "out_of_range"
    """out_of_range."""
    UNIMPLEMENTED = "unimplemented"
    """unimplemented."""
    INTERNAL = "internal"
    """internal."""
    UNAVAILABLE = "unavailable"
    """unavailable."""
    DATALOSS = "data_loss"
    """data_loss."""
    UNAUTHENTICATED = "unauthenticated"
    """unauthenticated."""


class RpcGrpcStatuscodeValues(Enum):
    OK = 0
    """OK."""
    CANCELLED = 1
    """CANCELLED."""
    UNKNOWN = 2
    """UNKNOWN."""
    INVALIDARGUMENT = 3
    """INVALID_ARGUMENT."""
    DEADLINEEXCEEDED = 4
    """DEADLINE_EXCEEDED."""
    NOTFOUND = 5
    """NOT_FOUND."""
    ALREADYEXISTS = 6
    """ALREADY_EXISTS."""
    PERMISSIONDENIED = 7
    """PERMISSION_DENIED."""
    RESOURCEEXHAUSTED = 8
    """RESOURCE_EXHAUSTED."""
    FAILEDPRECONDITION = 9
    """FAILED_PRECONDITION."""
    ABORTED = 10
    """ABORTED."""
    OUTOFRANGE = 11
    """OUT_OF_RANGE."""
    UNIMPLEMENTED = 12
    """UNIMPLEMENTED."""
    INTERNAL = 13
    """INTERNAL."""
    UNAVAILABLE = 14
    """UNAVAILABLE."""
    DATALOSS = 15
    """DATA_LOSS."""
    UNAUTHENTICATED = 16
    """UNAUTHENTICATED."""


class RpcSystemValues(Enum):
    GRPC = "grpc"
    """gRPC."""
    JAVARMI = "java_rmi"
    """Java RMI."""
    DOTNETWCF = "dotnet_wcf"
    """.NET WCF."""
    APACHEDUBBO = "apache_dubbo"
    """Apache Dubbo."""
    CONNECTRPC = "connect_rpc"
    """Connect RPC."""
