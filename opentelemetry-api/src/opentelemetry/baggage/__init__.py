# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Name/value pairs that travel alongside a trace.

Baggage is a set of name/value pairs carried in the current
:class:`~opentelemetry.context.Context` and propagated across process
boundaries by :class:`~opentelemetry.baggage.propagation.W3CBaggagePropagator`.
It lets a value set early in a request, such as an account identifier, be read
much later without threading it through every call.

Every function here that changes the baggage returns a new
:class:`~opentelemetry.context.Context` rather than modifying one, matching the
immutability of the context API. The reading functions, :func:`get_all` and
:func:`get_baggage`, return the pairs themselves.

Baggage is not added to spans automatically, and it is sent to every service
downstream, so a value that is sensitive or large does not belong in it.
"""

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
    """Read the raw baggage dict out of a context.

    Args:
        context: The context to read from. If ``None``, the current context is
            used.

    Returns:
        The baggage dict stored in the context, or an empty dict when the
        context holds no baggage or holds something that is not a dict. The
        returned dict is the stored one, so callers that intend to modify it
        must copy it first.
    """
    baggage = get_value(_BAGGAGE_KEY, context=context)
    if isinstance(baggage, dict):
        return baggage
    return {}


def _is_valid_key(name: str) -> bool:
    """Report whether ``name`` is usable as a baggage name.

    Args:
        name: The candidate baggage name.

    Returns:
        ``True`` when ``name`` is non-empty and made up only of RFC 7230 token
        characters, which is what the W3C Baggage header format permits.
    """
    return bool(name) and _KEY_CHARS.issuperset(name)


def _is_valid_property(property: str) -> bool:
    """Report whether ``property`` is a valid baggage list-member property.

    A property is the optional metadata that may follow a baggage value after
    a semicolon. It is either a bare key or a ``key=value`` pair.

    Args:
        property: One property, with no leading semicolon.

    Returns:
        ``True`` when the key half is a valid baggage name and the value half,
        if present, holds only permitted characters.
    """
    key, separator, value = property.partition("=")
    return _is_valid_key(key.strip(" \t")) and (not separator or _VALUE_CHARS.issuperset(value.strip(" \t")))


def _is_valid_value(value: object) -> bool:
    """Report whether ``value`` is usable as a baggage value.

    Args:
        value: The candidate baggage value. It is converted with :func:`str`
            before being checked, and any semicolon-delimited property that
            follows it is checked too.

    Returns:
        ``True`` when the value holds only printable US-ASCII characters other
        than the delimiters, and every property following it is valid.
    """
    value, *properties = str(value).split(";")
    # W3C Baggage allows optional whitespace between the value and ";"
    return _VALUE_CHARS.issuperset(value.rstrip(" \t")) and all(map(_is_valid_property, properties))


def _is_valid_pair(key: str, value: str) -> bool:
    """Report whether a name/value pair may be put in a baggage header.

    Args:
        key: The candidate baggage name.
        value: The candidate baggage value.

    Returns:
        ``True`` when both halves are valid on their own.
    """
    return _is_valid_key(key) and _is_valid_value(value)
