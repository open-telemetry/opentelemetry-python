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

import abc
from typing import Any, Sequence


class Encoder(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def encode(sdk_data: Sequence) -> Any:
        """
        Returns an encoded representation of the given sdk data sequence.
        The result should be an object-based encoding (e.g. pb2 objects or
        json dicts). If serialization is desired, it must be done via the
        serialize() wrapper method.
        """

    @classmethod
    @abc.abstractmethod
    def serialize(cls, sdk_data: Sequence) -> str:
        """
        This method should call self.encode() and then serialize the encoded
        data for return.
        """

    @staticmethod
    @abc.abstractmethod
    def content_type() -> str:
        """
        Http content type designation.
        """
