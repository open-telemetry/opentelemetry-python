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
from sys import version_info

from pkg_resources import iter_entry_points

from opentelemetry.context.context import Context, RuntimeContext

logger = logging.getLogger(__name__)
_RUNTIME_CONTEXT = None  # type: typing.Optional[RuntimeContext]


def get_value(key: str, context: typing.Optional[Context] = None) -> "object":
    """To access the local state of a concern, the RuntimeContext API
    provides a function which takes a context and a key as input,
    and returns a value.

    Args:
        key: The key of the value to retrieve.
        context: The context from which to retrieve the value, if None, the current context is used.
    """
    return context.get(key) if context is not None else get_current().get(key)


def set_value(
    key: str, value: "object", context: typing.Optional[Context] = None
) -> Context:
    """To record the local state of a cross-cutting concern, the
    RuntimeContext API provides a function which takes a context, a
    key, and a value as input, and returns an updated context
    which contains the new value.

    Args:
        key: The key of the entry to set
        value: The value of the entry to set
        context: The context to copy, if None, the current context is used
    """
    if context is None:
        context = get_current()
    new_values = context.copy()
    new_values[key] = value
    return Context(new_values)


def remove_value(
    key: str, context: typing.Optional[Context] = None
) -> Context:
    """To remove a value, this method returns a new context with the key
    cleared. Note that the removed value still remains present in the old
    context.

    Args:
        key: The key of the entry to remove
        context: The context to copy, if None, the current context is used
    """
    if context is None:
        context = get_current()
    new_values = context.copy()
    new_values.pop(key, None)
    return Context(new_values)


def get_current() -> Context:
    """To access the context associated with program execution,
    the RuntimeContext API provides a function which takes no arguments
    and returns a RuntimeContext.
    """

    global _RUNTIME_CONTEXT  # pylint: disable=global-statement
    if _RUNTIME_CONTEXT is None:
        # FIXME use a better implementation of a configuration manager to avoid having
        # to get configuration values straight from environment variables
        if version_info < (3, 5):
            # contextvars are not supported in 3.4, use thread-local storage
            default_context = "threadlocal_context"
        else:
            default_context = "contextvars_context"

        configured_context = environ.get(
            "OPENTELEMETRY_CONTEXT", default_context
        )  # type: str
        try:
            _RUNTIME_CONTEXT = next(
                iter_entry_points("opentelemetry_context", configured_context)
            ).load()()
        except Exception:  # pylint: disable=broad-except
            logger.error("Failed to load context: %s", configured_context)

    return _RUNTIME_CONTEXT.get_current()  # type:ignore


def set_current(context: Context) -> Context:
    """To associate a context with program execution, the Context
    API provides a function which takes a Context.

    Args:
        context: The context to use as current.
    """
    old_context = get_current()
    _RUNTIME_CONTEXT.set_current(context)  # type:ignore
    return old_context


def with_current_context(
    func: typing.Callable[..., "object"]
) -> typing.Callable[..., "object"]:
    """Capture the current context and apply it to the provided func."""

    caller_context = get_current()

    def call_with_current_context(
        *args: "object", **kwargs: "object"
    ) -> "object":
        try:
            backup = get_current()
            set_current(caller_context)
            return func(*args, **kwargs)
        finally:
            set_current(backup)

    return call_with_current_context
