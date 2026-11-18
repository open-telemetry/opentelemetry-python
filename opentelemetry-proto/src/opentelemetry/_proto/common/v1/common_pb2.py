# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# AUTO-GENERATED from "opentelemetry/proto/common/v1/common.proto"
# DO NOT EDIT MANUALLY
from __future__ import annotations

from struct import pack

from opentelemetry._proto._pyprotobuf import encode_int, encode_tag, encode_varint
from opentelemetry._proto._pyprotobuf.fields import WT_64BIT, WT_LEN, WT_VARINT, msg, string, u64
from opentelemetry._proto._pyprotobuf.message import Message

class AnyValue(Message):
    def __init__(self, string_value: str | None = None, bool_value: bool | None = None, int_value: int | None = None, double_value: float | None = None, array_value: ArrayValue | None = None, kvlist_value: KeyValueList | None = None, bytes_value: bytes | None = None, string_value_strindex: int | None = None) -> None:
        self._string_value = None
        self._bool_value = None
        self._int_value = None
        self._double_value = None
        self._array_value = None
        self._kvlist_value = None
        self._bytes_value = None
        self._string_value_strindex = None
        self._which_value = None
        if string_value is not None:
            self.string_value = string_value
        if bool_value is not None:
            self.bool_value = bool_value
        if int_value is not None:
            self.int_value = int_value
        if double_value is not None:
            self.double_value = double_value
        if array_value is not None:
            self.array_value = array_value
        if kvlist_value is not None:
            self.kvlist_value = kvlist_value
        if bytes_value is not None:
            self.bytes_value = bytes_value
        if string_value_strindex is not None:
            self.string_value_strindex = string_value_strindex

    def _select_value(self, name, value) -> None:
        for _f in ("string_value", "bool_value", "int_value", "double_value", "array_value", "kvlist_value", "bytes_value", "string_value_strindex",):
            setattr(self, f"_{_f}", value if _f == name else None)
        self._which_value = name

    @property
    def string_value(self):
        return self._string_value

    @string_value.setter
    def string_value(self, value) -> None:
        if value is None:
            self._string_value = None
            if self._which_value == "string_value":
                self._which_value = None
        else:
            self._select_value("string_value", value)

    @property
    def bool_value(self):
        return self._bool_value

    @bool_value.setter
    def bool_value(self, value) -> None:
        if value is None:
            self._bool_value = None
            if self._which_value == "bool_value":
                self._which_value = None
        else:
            self._select_value("bool_value", value)

    @property
    def int_value(self):
        return self._int_value

    @int_value.setter
    def int_value(self, value) -> None:
        if value is not None and not -9223372036854775808 <= value < 9223372036854775808:
            raise ValueError("Value out of range for int_value: " + repr(value))
        if value is None:
            self._int_value = None
            if self._which_value == "int_value":
                self._which_value = None
        else:
            self._select_value("int_value", value)

    @property
    def double_value(self):
        return self._double_value

    @double_value.setter
    def double_value(self, value) -> None:
        if value is None:
            self._double_value = None
            if self._which_value == "double_value":
                self._which_value = None
        else:
            self._select_value("double_value", value)

    @property
    def array_value(self):
        if self._array_value is None:
            self._select_value("array_value", ArrayValue())
        return self._array_value

    @array_value.setter
    def array_value(self, value) -> None:
        if value is None:
            self._array_value = None
            if self._which_value == "array_value":
                self._which_value = None
        else:
            if isinstance(value, dict):
                value = ArrayValue(**value)
            self._select_value("array_value", value)

    @property
    def kvlist_value(self):
        if self._kvlist_value is None:
            self._select_value("kvlist_value", KeyValueList())
        return self._kvlist_value

    @kvlist_value.setter
    def kvlist_value(self, value) -> None:
        if value is None:
            self._kvlist_value = None
            if self._which_value == "kvlist_value":
                self._which_value = None
        else:
            if isinstance(value, dict):
                value = KeyValueList(**value)
            self._select_value("kvlist_value", value)

    @property
    def bytes_value(self):
        return self._bytes_value

    @bytes_value.setter
    def bytes_value(self, value) -> None:
        if value is None:
            self._bytes_value = None
            if self._which_value == "bytes_value":
                self._which_value = None
        else:
            self._select_value("bytes_value", value)

    @property
    def string_value_strindex(self):
        return self._string_value_strindex

    @string_value_strindex.setter
    def string_value_strindex(self, value) -> None:
        if value is not None and not -2147483648 <= value < 2147483648:
            raise ValueError("Value out of range for string_value_strindex: " + repr(value))
        if value is None:
            self._string_value_strindex = None
            if self._which_value == "string_value_strindex":
                self._which_value = None
        else:
            self._select_value("string_value_strindex", value)

    def WhichOneof(self, oneof_name: str) -> str | None:
        if oneof_name == "value":
            return self._which_value
        return None

    def SerializeToString(self) -> bytes:
        result = b""
        if self._string_value is not None:
            _utf8 = self._string_value.encode('utf-8')
            result += encode_tag(1, WT_LEN) + encode_varint(len(_utf8)) + _utf8
        if self._bool_value is not None:
            result += encode_tag(2, WT_VARINT) + encode_varint(1 if self._bool_value else 0)
        if self._int_value is not None:
            result += encode_tag(3, WT_VARINT) + encode_int(self._int_value)
        if self._double_value is not None:
            result += encode_tag(4, WT_64BIT) + pack("<d", self._double_value)
        if self._array_value is not None:
            result += msg(5, self._array_value.SerializeToString())
        if self._kvlist_value is not None:
            result += msg(6, self._kvlist_value.SerializeToString())
        if self._bytes_value is not None:
            _bv = self._bytes_value
            result += encode_tag(7, WT_LEN) + encode_varint(len(_bv)) + _bv
        if self._string_value_strindex is not None:
            result += encode_tag(8, WT_VARINT) + encode_int(self._string_value_strindex)
        return result


class ArrayValue(Message):
    def __init__(self, values: list[AnyValue] | None = None) -> None:
        self.values = list(values) if values else []

    def SerializeToString(self) -> bytes:
        result = b""
        result += b"".join(msg(1, _v.SerializeToString()) for _v in self.values)
        return result


class KeyValueList(Message):
    def __init__(self, values: list[KeyValue] | None = None) -> None:
        self.values = list(values) if values else []

    def SerializeToString(self) -> bytes:
        result = b""
        result += b"".join(msg(1, _v.SerializeToString()) for _v in self.values)
        return result


class KeyValue(Message):
    def __init__(self, key: str | None = "", value: AnyValue | None = None, key_strindex: int | None = 0) -> None:
        self.key = key
        if isinstance(value, dict):
            value = AnyValue(**value)
        self.value = value
        self.key_strindex = key_strindex

    def SerializeToString(self) -> bytes:
        result = b""
        result += string(1, self.key)
        if self.value is not None:
            result += msg(2, self.value.SerializeToString())
        result += u64(3, self.key_strindex)
        return result


class InstrumentationScope(Message):
    def __init__(self, name: str | None = "", version: str | None = "", attributes: list[KeyValue] | None = None, dropped_attributes_count: int | None = 0) -> None:
        self.name = name
        self.version = version
        self.attributes = list(attributes) if attributes else []
        self.dropped_attributes_count = dropped_attributes_count

    def SerializeToString(self) -> bytes:
        result = b""
        result += string(1, self.name)
        result += string(2, self.version)
        result += b"".join(msg(3, _v.SerializeToString()) for _v in self.attributes)
        result += u64(4, self.dropped_attributes_count)
        return result


class EntityRef(Message):
    def __init__(self, schema_url: str | None = "", type: str | None = "", id_keys: list[str] | None = None, description_keys: list[str] | None = None) -> None:
        self.schema_url = schema_url
        self.type = type
        self.id_keys = list(id_keys) if id_keys else []
        self.description_keys = list(description_keys) if description_keys else []

    def SerializeToString(self) -> bytes:
        result = b""
        result += string(1, self.schema_url)
        result += string(2, self.type)
        result += b"".join(string(3, _v) for _v in self.id_keys)
        result += b"".join(string(4, _v) for _v in self.description_keys)
        return result
global___AnyValue = AnyValue
global___ArrayValue = ArrayValue
global___KeyValueList = KeyValueList
global___KeyValue = KeyValue
global___InstrumentationScope = InstrumentationScope
global___EntityRef = EntityRef
