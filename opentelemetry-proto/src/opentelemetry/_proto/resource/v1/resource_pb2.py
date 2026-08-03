"""Pure-Python equivalents of opentelemetry/proto/resource/v1/resource_pb2.py.

Field numbers:
    Resource  attributes=1  dropped_attributes_count=2
"""

from __future__ import annotations

from opentelemetry._proto.common.v1.common_pb2 import KeyValue
from opentelemetry._proto._pyprotobuf.fields import msg, u64


class Resource:
    def __init__(
        self,
        attributes: list[KeyValue] | None = None,
        dropped_attributes_count: int = 0,
    ):
        self.attributes: list[KeyValue] = list(attributes) if attributes else []
        self.dropped_attributes_count = dropped_attributes_count

    def SerializeToString(self) -> bytes:
        return (
            b"".join(msg(1, kv.SerializeToString()) for kv in self.attributes)
            + u64(2, self.dropped_attributes_count)
        )
