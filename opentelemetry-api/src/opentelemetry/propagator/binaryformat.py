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

from opentelemetry.context import BaseRuntimeContext


class BinaryFormat(abc.ABC):
    """API for serialization of span context into binary formats.

    This class provides an interface that enables converting span contexts
    to and from a binary format.
    """

    @staticmethod
    @abc.abstractmethod
    def to_bytes(context: BaseRuntimeContext) -> bytes:
        """Creates a byte representation of a Context.

        to_bytes should read values from a Context and return a data
        format to represent it, in bytes.

        Args:
            context: the Context to serialize.

        Returns:
            A bytes representation of the DistributedContext.

        """

    @staticmethod
    @abc.abstractmethod
    def from_bytes(
        context: BaseRuntimeContext, byte_representation: bytes
    ) -> None:
        """Populate context with data that existed in the byte representation.

        from_bytes should add values into the context from the data serialized in the
        byte_representation passed. If it is not possible to read in a proper
        DistributedContext, return None.

        Args:
            context: the Context to add values into.
            byte_representation: the bytes to deserialize.
        """
