# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Mapping
from logging import getLogger
from string import ascii_letters, digits
from types import MappingProxyType

from opentelemetry.context import create_key, get_value, set_value
from opentelemetry.context.context import Context

_BAGGAGE_KEY = create_key("baggage")
_logger = getLogger(__name__)

# RFC 7230 token characters
_KEY_CHARS = frozenset("!#$%&'*+-.^_`|~" + digits + ascii_letters)
# baggage-octet: printable US-ASCII except SP, DQUOTE, ",", ";" and "\"
_VALUE_CHARS = frozenset(map(chr, range(0x21, 0x7F))) - frozenset('",;\\')


def get_all(
    context: Context | None = None,
) -> Mapping[str, object]:
    """Returns the name/value pairs in the Baggage

    Args:
        context: The Context to use. If not set, uses current Context

    Returns:
        The name/value pairs in the Baggage
    """
    return MappingProxyType(_get_baggage_value(context=context))


def get_baggage(name: str, context: Context | None = None) -> object | None:
    """Provides access to the value for a name/value pair in the
    Baggage

    Args:
        name: The name of the value to retrieve
        context: The Context to use. If not set, uses current Context

    Returns:
        The value associated with the given name, or null if the given name is
        not present.
    """
    return _get_baggage_value(context=context).get(name)


def set_baggage(name: str, value: object, context: Context | None = None) -> Context:
    """Sets a value in the Baggage

    Args:
        name: The name of the value to set
        value: The value to set
        context: The Context to use. If not set, uses current Context

    Returns:
        A Context with the value updated
    """
    baggage = _get_baggage_value(context=context).copy()
    baggage[name] = value
    return set_value(_BAGGAGE_KEY, baggage, context=context)


def remove_baggage(name: str, context: Context | None = None) -> Context:
    """Removes a value from the Baggage

    Args:
        name: The name of the value to remove
        context: The Context to use. If not set, uses current Context

    Returns:
        A Context with the name/value removed
    """
    baggage = _get_baggage_value(context=context).copy()
    baggage.pop(name, None)

    return set_value(_BAGGAGE_KEY, baggage, context=context)


def clear(context: Context | None = None) -> Context:
    """Removes all values from the Baggage

    Args:
        context: The Context to use. If not set, uses current Context

    Returns:
        A Context with all baggage entries removed
    """
    return set_value(_BAGGAGE_KEY, {}, context=context)


def _get_baggage_value(context: Context | None = None) -> dict[str, object]:
    baggage = get_value(_BAGGAGE_KEY, context=context)
    if isinstance(baggage, dict):
        return baggage
    return {}


def _is_valid_key(name: str) -> bool:
    return bool(name) and _KEY_CHARS.issuperset(name)


def _is_valid_property(property: str) -> bool:
    key, separator, value = property.partition("=")
    return _is_valid_key(key.strip(" \t")) and (not separator or _VALUE_CHARS.issuperset(value.strip(" \t")))


def _is_valid_value(value: object) -> bool:
    value, *properties = str(value).split(";")
    # W3C Baggage allows optional whitespace between the value and ";"
    return _VALUE_CHARS.issuperset(value.rstrip(" \t")) and all(map(_is_valid_property, properties))


def _is_valid_pair(key: str, value: str) -> bool:
    return _is_valid_key(key) and _is_valid_value(value)
