# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Base class for the pure-Python protobuf message equivalents.

The protobuf-generated message classes support value equality and a readable
repr. Downstream code and its tests rely on comparing message instances with
``==``, so the pure-Python equivalents reproduce that behaviour here instead of
repeating it on every message class.
"""

from __future__ import annotations


class Message:
    def __eq__(self, other: object) -> bool:
        # Compare by wire bytes so equality matches protobuf semantics: proto3
        # omits default values, so a field left as None, "", 0 or b"" compares
        # equal to the same field set to its explicit default.
        return (
            type(self) is type(other)
            and self.SerializeToString() == other.SerializeToString()
        )

    # Protobuf messages are mutable and therefore unhashable; match that so a
    # message is never accidentally used as a dict key or set member.
    __hash__ = None

    def __repr__(self) -> str:
        fields = ", ".join(
            f"{name}={value!r}" for name, value in self.__dict__.items()
        )
        return f"{type(self).__name__}({fields})"

    def SerializePartialToString(self) -> bytes:
        # These messages have no required fields, so a partial serialization is
        # identical to a full one. protobuf exposes both, so mirror that.
        return self.SerializeToString()

    @classmethod
    def FromString(cls, data: bytes) -> "Message":
        # The OTLP export path only ever needs to decode the export-service
        # response, which is empty, so an empty instance is the correct result.
        return cls()
