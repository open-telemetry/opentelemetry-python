# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from enum import Enum
from typing import Final

from typing_extensions import deprecated

RPC_CONNECT_RPC_ERROR_CODE: Final = "rpc.connect_rpc.error_code"
"""
Deprecated: Replaced by `rpc.status_code`.
"""

RPC_CONNECT_RPC_REQUEST_METADATA_TEMPLATE: Final = "rpc.connect_rpc.request.metadata"
"""
Deprecated: Replaced by `rpc.request.header`.
"""

RPC_CONNECT_RPC_RESPONSE_METADATA_TEMPLATE: Final = "rpc.connect_rpc.response.metadata"
"""
Deprecated: Split to `rpc.response.header` for metadata sent before the response payload and `rpc.response.trailer` for metadata sent after it.
"""

RPC_GRPC_REQUEST_METADATA_TEMPLATE: Final = "rpc.grpc.request.metadata"
"""
Deprecated: Replaced by `rpc.request.header`.
"""

RPC_GRPC_RESPONSE_METADATA_TEMPLATE: Final = "rpc.grpc.response.metadata"
"""
Deprecated: Split to `rpc.response.header` for metadata sent before the response payload and `rpc.response.trailer` for metadata sent after it.
"""

RPC_GRPC_STATUS_CODE: Final = "rpc.grpc.status_code"
"""
Deprecated: Use string representation of the gRPC status code on the `rpc.status_code` attribute.
"""

RPC_JSONRPC_ERROR_CODE: Final = "rpc.jsonrpc.error_code"
"""
Deprecated: Use string representation of the error code on the `rpc.status_code` attribute.
"""

RPC_JSONRPC_ERROR_MESSAGE: Final = "rpc.jsonrpc.error_message"
"""
Deprecated: Use the span status description when reporting JSON-RPC spans.
"""

RPC_JSONRPC_REQUEST_ID: Final = "rpc.jsonrpc.request_id"
"""
Deprecated: Replaced by `jsonrpc.request.id`.
"""

RPC_JSONRPC_VERSION: Final = "rpc.jsonrpc.version"
"""
Deprecated: Replaced by `jsonrpc.protocol.version`.
"""

RPC_MESSAGE_COMPRESSED_SIZE: Final = "rpc.message.compressed_size"
"""
Deprecated: Deprecated, no replacement at this time.
"""

RPC_MESSAGE_ID: Final = "rpc.message.id"
"""
Deprecated: Deprecated, no replacement at this time.
"""

RPC_MESSAGE_TYPE: Final = "rpc.message.type"
"""
Deprecated: Deprecated, no replacement at this time.
"""

RPC_MESSAGE_UNCOMPRESSED_SIZE: Final = "rpc.message.uncompressed_size"
"""
Deprecated: Deprecated, no replacement at this time.
"""

RPC_METHOD: Final = "rpc.method"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.rpc_attributes.RPC_METHOD`.
"""

RPC_METHOD_ORIGINAL: Final = "rpc.method_original"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.rpc_attributes.RPC_METHOD_ORIGINAL`.
"""

RPC_REQUEST_HEADER_TEMPLATE: Final = "rpc.request.header"
"""
RPC request headers or metadata, `<key>` being the normalized header name (lowercase), the value being the header values.
Note: Instrumentations SHOULD require an explicit configuration of which headers are to be captured.
Including all request headers can be a security risk - explicit configuration helps avoid leaking sensitive information.

For example, a header `my-custom-key` with value `["1.2.3.4", "1.2.3.5"]` SHOULD be recorded as
the `rpc.request.header.my-custom-key` attribute with value `["1.2.3.4", "1.2.3.5"]`

The attribute value MUST consist of either multiple header values as an array of
strings or a single-item array containing a possibly comma-concatenated string,
depending on the way the RPC library provides access to headers.

Values that the RPC system exposes as binary data, or that are otherwise not valid
UTF-8 strings, SHOULD be base64-encoded when recorded.
"""

RPC_REQUEST_METADATA_TEMPLATE: Final = "rpc.request.metadata"
"""
Deprecated: Replaced by `rpc.request.header`.
"""

RPC_RESPONSE_HEADER_TEMPLATE: Final = "rpc.response.header"
"""
RPC response headers or metadata sent before the response payload, `<key>` being the normalized header name (lowercase), the value being the header values.
Note: Instrumentations SHOULD require an explicit configuration of which headers are to be captured.
Including all response headers can be a security risk - explicit configuration helps avoid leaking sensitive information.

For example, a header `my-custom-key` with value `["attribute_value"]` SHOULD be recorded as
the `rpc.response.header.my-custom-key` attribute with value `["attribute_value"]`

The attribute value MUST consist of either multiple header values as an array of
strings or a single-item array containing a possibly comma-concatenated string,
depending on the way the RPC library provides access to headers.

Values that the RPC system exposes as binary data, or that are otherwise not valid
UTF-8 strings, SHOULD be base64-encoded when recorded.
"""

RPC_RESPONSE_METADATA_TEMPLATE: Final = "rpc.response.metadata"
"""
Deprecated: Split to `rpc.response.header` for metadata sent before the response payload and `rpc.response.trailer` for metadata sent after it.
"""

RPC_RESPONSE_STATUS_CODE: Final = "rpc.response.status_code"
"""
Deprecated: Replaced by `rpc.status_code`.
"""

RPC_RESPONSE_TRAILER_TEMPLATE: Final = "rpc.response.trailer"
"""
RPC response trailers or metadata sent after the response payload, `<key>` being the normalized trailer name (lowercase), the value being the trailer values.
Note: Instrumentations SHOULD require an explicit configuration of which trailers are to be captured.
Including all response trailers can be a security risk - explicit configuration helps avoid leaking sensitive information.

For example, a trailer `my-custom-key` with value `["attribute_value"]` SHOULD be recorded as
the `rpc.response.trailer.my-custom-key` attribute with value `["attribute_value"]`

The attribute value MUST consist of either multiple trailer values as an array of
strings or a single-item array containing a possibly comma-concatenated string,
depending on the way the RPC library provides access to trailers.

Values that the RPC system exposes as binary data, or that are otherwise not valid
UTF-8 strings, SHOULD be base64-encoded when recorded.
"""

RPC_SERVICE: Final = "rpc.service"
"""
Deprecated: Value should be included in `rpc.method` which is expected to be a fully-qualified name.
"""

RPC_STATUS_CODE: Final = "rpc.status_code"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.rpc_attributes.RPC_STATUS_CODE`.
"""

RPC_SYSTEM: Final = "rpc.system"
"""
Deprecated: Replaced by `rpc.system.name`.
"""

RPC_SYSTEM_NAME: Final = "rpc.system.name"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.rpc_attributes.RPC_SYSTEM_NAME`.
"""


@deprecated("The attribute rpc.connect_rpc.error_code is deprecated - Replaced by `rpc.status_code`")
class RpcConnectRpcErrorCodeValues(Enum):
    CANCELLED = "cancelled"
    """cancelled."""
    UNKNOWN = "unknown"
    """unknown."""
    INVALID_ARGUMENT = "invalid_argument"
    """invalid_argument."""
    DEADLINE_EXCEEDED = "deadline_exceeded"
    """deadline_exceeded."""
    NOT_FOUND = "not_found"
    """not_found."""
    ALREADY_EXISTS = "already_exists"
    """already_exists."""
    PERMISSION_DENIED = "permission_denied"
    """permission_denied."""
    RESOURCE_EXHAUSTED = "resource_exhausted"
    """resource_exhausted."""
    FAILED_PRECONDITION = "failed_precondition"
    """failed_precondition."""
    ABORTED = "aborted"
    """aborted."""
    OUT_OF_RANGE = "out_of_range"
    """out_of_range."""
    UNIMPLEMENTED = "unimplemented"
    """unimplemented."""
    INTERNAL = "internal"
    """internal."""
    UNAVAILABLE = "unavailable"
    """unavailable."""
    DATA_LOSS = "data_loss"
    """data_loss."""
    UNAUTHENTICATED = "unauthenticated"
    """unauthenticated."""


@deprecated(
    "The attribute rpc.grpc.status_code is deprecated - Use string representation of the gRPC status code on the `rpc.status_code` attribute"
)
class RpcGrpcStatusCodeValues(Enum):
    OK = 0
    """OK."""
    CANCELLED = 1
    """CANCELLED."""
    UNKNOWN = 2
    """UNKNOWN."""
    INVALID_ARGUMENT = 3
    """INVALID_ARGUMENT."""
    DEADLINE_EXCEEDED = 4
    """DEADLINE_EXCEEDED."""
    NOT_FOUND = 5
    """NOT_FOUND."""
    ALREADY_EXISTS = 6
    """ALREADY_EXISTS."""
    PERMISSION_DENIED = 7
    """PERMISSION_DENIED."""
    RESOURCE_EXHAUSTED = 8
    """RESOURCE_EXHAUSTED."""
    FAILED_PRECONDITION = 9
    """FAILED_PRECONDITION."""
    ABORTED = 10
    """ABORTED."""
    OUT_OF_RANGE = 11
    """OUT_OF_RANGE."""
    UNIMPLEMENTED = 12
    """UNIMPLEMENTED."""
    INTERNAL = 13
    """INTERNAL."""
    UNAVAILABLE = 14
    """UNAVAILABLE."""
    DATA_LOSS = 15
    """DATA_LOSS."""
    UNAUTHENTICATED = 16
    """UNAUTHENTICATED."""


@deprecated("The attribute rpc.message.type is deprecated - Deprecated, no replacement at this time")
class RpcMessageTypeValues(Enum):
    SENT = "SENT"
    """sent."""
    RECEIVED = "RECEIVED"
    """received."""


@deprecated("The attribute rpc.system is deprecated - Replaced by `rpc.system.name`")
class RpcSystemValues(Enum):
    GRPC = "grpc"
    """gRPC."""
    JAVA_RMI = "java_rmi"
    """Java RMI."""
    DOTNET_WCF = "dotnet_wcf"
    """.NET WCF."""
    APACHE_DUBBO = "apache_dubbo"
    """Apache Dubbo."""
    CONNECT_RPC = "connect_rpc"
    """Connect RPC."""
    ONC_RPC = "onc_rpc"
    """[ONC RPC (Sun RPC)](https://datatracker.ietf.org/doc/html/rfc5531)."""
    JSONRPC = "jsonrpc"
    """JSON-RPC."""


@deprecated(
    "Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.rpc_attributes.RpcSystemNameValues`."
)
class RpcSystemNameValues(Enum):
    GRPC = "grpc"
    """Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.rpc_attributes.RpcSystemNameValues.GRPC`."""
    DUBBO = "dubbo"
    """Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.rpc_attributes.RpcSystemNameValues.DUBBO`."""
    CONNECTRPC = "connectrpc"
    """[Connect RPC](https://connectrpc.com/)."""
    JSONRPC = "jsonrpc"
    """[JSON-RPC](https://www.jsonrpc.org/)."""
