# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# AUTO-GENERATED from "opentelemetry/proto/resource/v1/resource.proto"
# DO NOT EDIT MANUALLY
from __future__ import annotations

from opentelemetry._proto._pyprotobuf.fields import msg, u64
from opentelemetry._proto._pyprotobuf.message import Message
from opentelemetry._proto.common.v1.common_pb2 import EntityRef
from opentelemetry._proto.common.v1.common_pb2 import KeyValue

class Resource(Message):
    def __init__(self, attributes: list[KeyValue] | None = None, dropped_attributes_count: int | None = 0, entity_refs: list[EntityRef] | None = None) -> None:
        self.attributes = list(attributes) if attributes else []
        self.dropped_attributes_count = dropped_attributes_count
        self.entity_refs = list(entity_refs) if entity_refs else []

    def SerializeToString(self) -> bytes:
        result = b""
        result += b"".join(msg(1, _v.SerializeToString()) for _v in self.attributes)
        result += u64(2, self.dropped_attributes_count)
        result += b"".join(msg(3, _v.SerializeToString()) for _v in self.entity_refs)
        return result
global___Resource = Resource
