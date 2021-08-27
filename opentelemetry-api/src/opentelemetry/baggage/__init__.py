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

from logging import getLogger
from re import compile as compile_
from types import MappingProxyType
from typing import Mapping, Optional

from opentelemetry.context import create_key, get_value, set_value
from opentelemetry.context.context import Context

_BAGGAGE_KEY = create_key("baggage")
_logger = getLogger(__name__)

# The following regular expressions are taken from
# https://github.com/open-telemetry/opentelemetry-go/blob/4bf6150fa94e18bdf01c96ed78ee6d1c76f8e308/baggage/baggage.go#L36-L55
_key_regex = compile_(r"[!#-'*+-.0-9A-Z^-z|~]+")
_value_regex = compile_(r"[!#-+.-:<-\[\]-~-]*")


def get_all(
    context: Optional[Context] = None,
) -> Mapping[str, object]:
    """Returns the name/value pairs in the Baggage

    Args:
        context: The Context to use. If not set, uses current Context

    Returns:
        The name/value pairs in the Baggage
    """
    baggage = get_value(_BAGGAGE_KEY, context=context)
    if isinstance(baggage, dict):
        return MappingProxyType(baggage)
    return MappingProxyType({})


def get_baggage(
    name: str, context: Optional[Context] = None
) -> Optional[object]:
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
    name: str, value: object, context: Optional[Context] = None
) -> Context:
    """Sets a value in the Baggage

    Args:
        name: The name of the value to set
        value: The value to set
        context: The Context to use. If not set, uses current Context

    Returns:
        A Context with the value updated
    """
    if _key_regex.fullmatch(name) is None or (
        _value_regex.fullmatch(str(value)) is None
    ):
        _logger.warning(
            "name %s and value %s have been discarded", name, value
        )
        return None
    baggage = dict(get_all(context=context))
    baggage[name] = value
    return set_value(_BAGGAGE_KEY, baggage, context=context)


def remove_baggage(name: str, context: Optional[Context] = None) -> Context:
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


def clear(context: Optional[Context] = None) -> Context:
    """Removes all values from the Baggage

    Args:
        context: The Context to use. If not set, uses current Context

    Returns:
        A Context with all baggage entries removed
    """
    return set_value(_BAGGAGE_KEY, {}, context=context)
