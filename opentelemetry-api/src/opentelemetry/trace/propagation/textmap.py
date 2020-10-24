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
import typing

from opentelemetry.context.context import Context

TextMapPropagatorT = typing.TypeVar("TextMapPropagatorT")
CarrierValT = typing.Union[typing.List[str], str]

Setter = typing.Callable[[TextMapPropagatorT, str, str], None]


class Getter(typing.Generic[TextMapPropagatorT]):
    """This class implements a Getter that enables extracting propagated
    fields from a carrier

    """

    def get(self, carrier: TextMapPropagatorT, key: str) -> typing.List[str]:
        """Function that can retrieve zero
        or more values from the carrier. In the case that
        the value does not exist, returns an empty list.

        Args:
            carrier: An object which contains values that are used to
                    construct a Context.
            key: key of a field in carrier.
        Returns: first value of the propagation key or an empty list if the
                key doesn't exist.
        """
        raise NotImplementedError()

    def keys(self, carrier: TextMapPropagatorT) -> typing.List[str]:
        """Function that can retrieve all the keys in a carrier object.

        Args:
            carrier: An object which contains values that are
                used to construct a Context.
        Returns:
            list of keys from the carrier.
        """
        raise NotImplementedError()


class DictGetter(Getter[typing.Dict[str, CarrierValT]]):
    def get(
        self, carrier: typing.Dict[str, CarrierValT], key: str
    ) -> typing.List[str]:
        val = carrier.get(key, [])
        if isinstance(val, typing.Iterable) and not isinstance(val, str):
            return list(val)
        return [val]

    def keys(self, carrier: typing.Dict[str, CarrierValT]) -> typing.List[str]:
        return list(carrier.keys())


class TextMapPropagator(abc.ABC):
    """This class provides an interface that enables extracting and injecting
    context into headers of HTTP requests. HTTP frameworks and clients
    can integrate with TextMapPropagator by providing the object containing the
    headers, and a getter and setter function for the extraction and
    injection of values, respectively.

    """

    @abc.abstractmethod
    def extract(
        self,
        getter: Getter[TextMapPropagatorT],
        carrier: TextMapPropagatorT,
        context: typing.Optional[Context] = None,
    ) -> Context:
        """Create a Context from values in the carrier.

        The extract function should retrieve values from the carrier
        object using getter, and use values to populate a
        Context value and return it.

        Args:
            getter: a function that can retrieve zero
                or more values from the carrier. In the case that
                the value does not exist, return an empty list.
            carrier: and object which contains values that are
                used to construct a Context. This object
                must be paired with an appropriate getter
                which understands how to extract a value from it.
            context: an optional Context to use. Defaults to current
                context if not set.
        Returns:
            A Context with configuration found in the carrier.

        """

    @abc.abstractmethod
    def inject(
        self,
        set_in_carrier: Setter[TextMapPropagatorT],
        carrier: TextMapPropagatorT,
        context: typing.Optional[Context] = None,
    ) -> None:
        """Inject values from a Context into a carrier.

        inject enables the propagation of values into HTTP clients or
        other objects which perform an HTTP request. Implementations
        should use the set_in_carrier method to set values on the
        carrier.

        Args:
            set_in_carrier: A setter function that can set values
                on the carrier.
            carrier: An object that a place to define HTTP headers.
                Should be paired with set_in_carrier, which should
                know how to set header values on the carrier.
            context: an optional Context to use. Defaults to current
                context if not set.

        """
