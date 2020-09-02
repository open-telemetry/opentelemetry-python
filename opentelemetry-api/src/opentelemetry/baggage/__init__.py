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

import typing
from types import MappingProxyType

from opentelemetry.context import get_value, set_value
from opentelemetry.context.context import Context

_BAGGAGE_KEY = "baggage"


def get_all(
    context: typing.Optional[Context] = None,
) -> typing.Mapping[str, object]:
    """Returns the name/value pairs in the Baggage

    Args:
        context: The Context to use. If not set, uses current Context

    Returns:
        The name/value pairs in the Baggage
    """
    baggage = get_value(_BAGGAGE_KEY, context=context)
    if isinstance(baggage, dict):
        return MappingProxyType(baggage.copy())
    return MappingProxyType({})


def get_baggage(
    name: str, context: typing.Optional[Context] = None
) -> typing.Optional[object]:
    """Provides access to the value for a name/value pair in the
    Baggage

    Args:
        name: The name of the value to retrieve
        context: The Context to use. If not set, uses current Context

    Returns:
        The value associated with the given name, or null if the given name is
        not present.
    """
    return get_all(context=context).get(name)


def set_baggage(
    name: str, value: object, context: typing.Optional[Context] = None
) -> Context:
    """Sets a value in the Baggage

    Args:
        name: The name of the value to set
        value: The value to set
        context: The Context to use. If not set, uses current Context

    Returns:
        A Context with the value updated
    """
    baggage = dict(get_all(context=context))
    baggage[name] = value
    return set_value(_BAGGAGE_KEY, baggage, context=context)


def remove_baggage(
    name: str, context: typing.Optional[Context] = None
) -> Context:
    """Removes a value from the Baggage

    Args:
        name: The name of the value to remove
        context: The Context to use. If not set, uses current Context

    Returns:
        A Context with the name/value removed
    """
    baggage = dict(get_all(context=context))
    baggage.pop(name, None)

    return set_value(_BAGGAGE_KEY, baggage, context=context)


def clear(context: typing.Optional[Context] = None) -> Context:
    """Removes all values from the Baggage

    Args:
        context: The Context to use. If not set, uses current Context

    Returns:
        A Context with all baggage entries removed
    """
    return set_value(_BAGGAGE_KEY, {}, context=context)
