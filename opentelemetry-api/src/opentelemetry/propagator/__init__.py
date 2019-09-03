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
from opentelemetry import loader
import opentelemetry.propagator.httptextformat as httptextformat
import opentelemetry.propagator.binaryformat as binaryformat
from opentelemetry.context import BaseRuntimeContext, Context


class Propagator(abc.ABC):
    """Class which encapsulates propagation of values to and from context.

    In contract to using the formatters directly, a propagator object can
    help own configuration around which formatters to use, as well as
    help simplify the work require for integrations to use the intended
    formatters.
    """

    def __init__(
        self,
        context: BaseRuntimeContext,
        http_format: httptextformat.HTTPTextFormat,
        binary_format: binaryformat.BinaryFormat,
    ):
        self._context = context
        self._http_format = http_format
        self._binary_format = binary_format

    @classmethod
    def create(
        cls,
        http_format: httptextformat.HTTPTextFormat,
        binary_format: binaryformat.BinaryFormat,
    ) -> "Propagator":
        """Create a propagator with the current context."""
        return Propagator(Context, http_format, binary_format)

    @abc.abstractmethod
    def extract(
        self, get_from_carrier: httptextformat.Getter, carrier: object
    ):
        """Extract context data from the carrier, add to the context.

        Using the http_format specified in the constructor, extract the
        data form the carrier passed and add values into the context object.

        Args:
            get_from_carrier: a function that can retrieve zero
                or more values from the carrier. In the case that
                the value does not exist, return an empty list.
            carrier: and object which contains values that are
                used to construct a SpanContext. This object
                must be paired with an appropriate get_from_carrier
                which understands how to extract a value from it.
        """

    @abc.abstractmethod
    def inject(
        self, set_in_carrier: httptextformat.Setter, carrier: object
    ) -> None:
        """Inject values from context into a carrier.

        inject enables the propagation of values into HTTP clients or
        other objects which perform an HTTP request. Using the
        httptextformat configured, inject the context data into
        the carrier with the set_in_carrier method passed.

        Args:
            set_in_carrier: A setter function that can set values
                on the carrier.
            carrier: An object that a place to define HTTP headers.
                Should be paired with set_in_carrier, which should
                know how to set header values on the carrier.
        """

    @abc.abstractmethod
    def from_bytes(self, byte_representation: bytes) -> None:
        """Populate context with data that existed in the byte representation.

        Using the configured binary_format, extract values from the bytes object
        passed into the context object configured.

        Args:
            byte_representation: the bytes to deserialize.
        """

    @abc.abstractmethod
    def to_bytes(self) -> bytes:
        """Creates a byte representation of the context configured.

        to_bytes should read values from the configured context and 
        return a bytes object to represent it.

        Returns:
            A bytes representation of the DistributedContext.
        """


def set_propagator(propagator_instance: Propagator) -> None:
    """Set the propagator instance singleton.
    """
    global _PROPAGATOR
    _PROPAGATOR = propagator_instance


def global_propagator() -> Propagator:
    """Return the singleton propagator instance."""
    return _PROPAGATOR


_PROPAGATOR = None  # type: typing.Optional[Propagator]
