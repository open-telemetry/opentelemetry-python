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

import logging
import typing
from os import environ

from pkg_resources import iter_entry_points

from opentelemetry.context.context import Context

logger = logging.getLogger(__name__)
_CONTEXT = None  # type: typing.Optional[Context]


def create_key(key: str) -> "object":
    # FIXME Implement this
    raise NotImplementedError


def get_value(key: str, context: typing.Optional[Context] = None) -> "object":
    """
    To access the local state of an concern, the Context API
    provides a function which takes a context and a key as input,
    and returns a value.

    Args:
        key: The key of the value to retrieve.
        context: The context from which to retrieve the value, if None, the current context is used.
    """
    return context.get_value(key) if context else get_current().get_value(key)


def set_value(
    key: str, value: "object", context: typing.Optional[Context] = None
) -> Context:
    """
    To record the local state of a cross-cutting concern, the
    Context API provides a function which takes a context, a
    key, and a value as input, and returns an updated context
    which contains the new value.

    Args:
        key: The key of the entry to set
        value: The value of the entry to set
        context: The context to copy, if None, the current context is used
    """
    new_context = context.copy() if context else get_current().copy()
    new_context.set_value(key, value)
    return new_context


def remove_value(
    key: str, context: typing.Optional[Context] = None
) -> Context:
    """
    To remove a value, this method returns a new context with the key cleared.
    Note that the removed value still remains present in the old context.

    Args:
        key: The key of the entry to remove
        context: The context to copy, if None, the current context is used
    """
    new_context = context.copy() if context else get_current().copy()
    new_context.remove_value(key)
    return new_context


def get_current() -> Context:
    """
    To access the context associated with program execution,
    the Context API provides a function which takes no arguments
    and returns a Context.
    """
    global _CONTEXT  # pylint: disable=global-statement
    if _CONTEXT is None:
        # FIXME use a better implementation of a configuration manager to avoid having
        # to get configuration values straight from environment variables

        configured_context = environ.get(
            "OPENTELEMETRY_CONTEXT", "default_context"
        )  # type: str
        _CONTEXT = next(
            iter_entry_points("opentelemetry_context", configured_context)
        ).load()()
    return _CONTEXT  # type: ignore


def set_current(context: Context) -> None:
    """
    To associate a context with program execution, the Context
    API provides a function which takes a Context.

    Args:
        context: The context to use as current.
    """
    global _CONTEXT  # pylint: disable=global-statement
    _CONTEXT = context


__all__ = [
    "get_value",
    "set_value",
    "remove_value",
    "get_current",
    "set_current",
    "Context",
]
