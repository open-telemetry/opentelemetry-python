"""Pure-Python equivalents of opentelemetry/proto/common/v1/common_pb2.py.

Field numbers:
    AnyValue (oneof value)  string_value=1  bool_value=2  int_value=3
                            double_value=4  array_value=5  kvlist_value=6
                            bytes_value=7
    ArrayValue              values=1
    KeyValueList            values=1
    KeyValue                key=1  value=2
    InstrumentationScope    name=1  version=2  attributes=3
                            dropped_attributes_count=4
"""

from __future__ import annotations

from struct import pack

from opentelemetry._proto._pyprotobuf import encode_int, encode_tag, encode_varint

from opentelemetry._proto._pyprotobuf.fields import msg, string, u64, WT_LEN, WT_VARINT, WT_64BIT


class AnyValue:
    """Oneof value container — exactly one field is set."""

    def __init__(
        self,
        string_value: str | None = None,
        bool_value: bool | None = None,
        int_value: int | None = None,
        double_value: float | None = None,
        array_value: "ArrayValue | None" = None,
        kvlist_value: "KeyValueList | None" = None,
        bytes_value: bytes | None = None,
    ):
        self._which: str | None = None
        if string_value is not None:
            self.string_value = string_value
            self._which = "string_value"
        elif bool_value is not None:
            self.bool_value = bool_value
            self._which = "bool_value"
        elif int_value is not None:
            self.int_value = int_value
            self._which = "int_value"
        elif double_value is not None:
            self.double_value = double_value
            self._which = "double_value"
        elif array_value is not None:
            self.array_value = array_value
            self._which = "array_value"
        elif kvlist_value is not None:
            self.kvlist_value = kvlist_value
            self._which = "kvlist_value"
        elif bytes_value is not None:
            self.bytes_value = bytes_value
            self._which = "bytes_value"

    def WhichOneof(self, oneof_name: str) -> str | None:
        if oneof_name == "value":
            return self._which
        return None

    def SerializeToString(self) -> bytes:
        # oneof: always written even when the value equals the proto3 default.
        if self._which == "string_value":
            utf8 = self.string_value.encode("utf-8")
            return encode_tag(1, WT_LEN) + encode_varint(len(utf8)) + utf8
        if self._which == "bool_value":
            return encode_tag(2, WT_VARINT) + encode_varint(1 if self.bool_value else 0)
        if self._which == "int_value":
            return encode_tag(3, WT_VARINT) + encode_int(self.int_value)
        if self._which == "double_value":
            return encode_tag(4, WT_64BIT) + pack("<d", self.double_value)
        if self._which == "array_value":
            return msg(5, self.array_value.SerializeToString())
        if self._which == "kvlist_value":
            return msg(6, self.kvlist_value.SerializeToString())
        if self._which == "bytes_value":
            bv = self.bytes_value
            return encode_tag(7, WT_LEN) + encode_varint(len(bv)) + bv
        return b""


class ArrayValue:
    def __init__(self, values: list[AnyValue] | None = None):
        self.values: list[AnyValue] = list(values) if values else []

    def SerializeToString(self) -> bytes:
        return b"".join(msg(1, v.SerializeToString()) for v in self.values)


class KeyValueList:
    def __init__(self, values: "list[KeyValue] | None" = None):
        self.values: list[KeyValue] = list(values) if values else []

    def SerializeToString(self) -> bytes:
        return b"".join(msg(1, kv.SerializeToString()) for kv in self.values)


class KeyValue:
    def __init__(self, key: str = "", value: AnyValue | None = None):
        self.key = key
        self.value = value

    def SerializeToString(self) -> bytes:
        result = string(1, self.key)
        if self.value is not None:
            result += msg(2, self.value.SerializeToString())
        return result


class InstrumentationScope:
    def __init__(
        self,
        name: str = "",
        version: str = "",
        attributes: list[KeyValue] | None = None,
        dropped_attributes_count: int = 0,
    ):
        self.name = name
        self.version = version
        self.attributes: list[KeyValue] = list(attributes) if attributes else []
        self.dropped_attributes_count = dropped_attributes_count

    def SerializeToString(self) -> bytes:
        return (
            string(1, self.name)
            + string(2, self.version)
            + b"".join(msg(3, kv.SerializeToString()) for kv in self.attributes)
            + u64(4, self.dropped_attributes_count)
        )
