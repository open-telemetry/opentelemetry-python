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

Setter = typing.Callable[[TextMapPropagatorT, str, str], None]


def default_get(carrier: TextMapPropagatorT, key: str) -> typing.List[str]:
    return [carrier.get(key)] if carrier.get(key) else []


def default_keys(carrier: TextMapPropagatorT) -> typing.List[str]:
    return list(carrier.keys())


GetterGetFunction = typing.Callable[
    [TextMapPropagatorT, str], typing.List[str]
]
GetterKeysFunction = typing.Callable[[TextMapPropagatorT], typing.List[str]]


class Getter:
    """This class implements a Getter that enables extracting propagated
    fields from a carrier

    """

    def __init__(
        self,
        get: GetterGetFunction[TextMapPropagatorT] = default_get,
        keys: GetterKeysFunction[TextMapPropagatorT] = default_keys,
    ):
        self._get = get
        self._keys = keys

    def get(self, carrier: TextMapPropagatorT, key: str) -> typing.List[str]:
        """Function that can retrieve zero
        or more values from the carrier. In the case that
        the value does not exist, returns an empty list.

        Args:
            carrier: and object which contains values that are
                used to construct a Context. This object
                must be paired with an appropriate get_from_carrier
                which understands how to extract a value from it.
            key: key of a field in carrier.
        Returns:
            first value of the propagation key or an empty list if the key doesn't exist.
        """
        return self._get(carrier, key)

    def keys(self, carrier: TextMapPropagatorT) -> typing.List[str]:
        """Function that can retrieve all the keys in a carrier object.

        Args:
            carrier: and object which contains values that are
                used to construct a Context. This object
                must be paired with an appropriate get_from_carrier
                which understands how to extract a value from it.
        Returns:
            list of keys from the carrier.
        """
        return self._keys(carrier)


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
        get_from_carrier: Getter,
        carrier: TextMapPropagatorT,
        context: typing.Optional[Context] = None,
    ) -> Context:
        """Create a Context from values in the carrier.

        The extract function should retrieve values from the carrier
        object using get_from_carrier, and use values to populate a
        Context value and return it.

        Args:
            get_from_carrier: a function that can retrieve zero
                or more values from the carrier. In the case that
                the value does not exist, return an empty list.
            carrier: and object which contains values that are
                used to construct a Context. This object
                must be paired with an appropriate get_from_carrier
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
