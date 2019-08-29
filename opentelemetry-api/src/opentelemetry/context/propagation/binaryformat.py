# Copyright 2019, OpenTelemetry Authors
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
import typing

from opentelemetry.trace import SpanContext


class BinaryFormat(abc.ABC):
    """API for serialization of span context into binary formats.

    This class provides an interface that enables converting span contexts
    to and from a binary format.
    """

    @staticmethod
    @abc.abstractmethod
    def to_bytes(context: SpanContext) -> bytes:
        """Creates a byte representation of a SpanContext.

        to_bytes should read values from a SpanContext and return a data
        format to represent it, in bytes.

        Args:
            context: the SpanContext to serialize

        Returns:
            A bytes representation of the SpanContext.

        """

    @staticmethod
    @abc.abstractmethod
    def from_bytes(byte_representation: bytes) -> typing.Optional[SpanContext]:
        """Return a SpanContext that was represented by bytes.

        from_bytes should return back a SpanContext that was constructed from
        the data serialized in the byte_representation passed. If it is not
        possible to read in a proper SpanContext, return None.

        Args:
            byte_representation: the bytes to deserialize

        Returns:
            A bytes representation of the SpanContext if it is valid.
            Otherwise return None.

        """
