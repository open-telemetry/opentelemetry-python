from enum import Enum


class Protocol(Enum):
    GRPC = "grpc"
    THRIFT = "thrift"
    THRIFT_HTTP = "thrift_http"
