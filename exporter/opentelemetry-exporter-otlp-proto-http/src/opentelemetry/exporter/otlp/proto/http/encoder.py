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

from abc import ABC, abstractstaticmethod
from typing import Generic, Sequence, TypeVar

_SDKDataT = TypeVar("_SDKDataT")
_ExportServiceRequestT = TypeVar("_ExportServiceRequestT")


class _ProtobufEncoderMixin(ABC, Generic[_SDKDataT, _ExportServiceRequestT]):
    @classmethod
    def serialize(cls, sdk_data: Sequence[_SDKDataT]) -> str:
        return cls.encode(sdk_data).SerializeToString()

    @abstractstaticmethod
    def encode(sdk_data: Sequence[_SDKDataT]) -> _ExportServiceRequestT:
        pass
