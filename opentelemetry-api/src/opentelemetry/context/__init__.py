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


def _copy_context(context: typing.Optional[Context]) -> Context:
    if context is not None:
        return context.copy()
    return get_current().copy()


def create_key(key: str) -> "object":
    # FIXME Implement this
    raise NotImplementedError


def get_value(key: str, context: typing.Optional[Context] = None) -> "object":
    if context is not None:
        return context.get_value(key)
    return get_current().get_value(key)


def set_value(
    key: str, value: "object", context: typing.Optional[Context] = None
) -> Context:
    new_context = _copy_context(context)
    new_context.set_value(key, value)
    return new_context


def remove_value(
    key: str, context: typing.Optional[Context] = None
) -> Context:
    new_context = _copy_context(context)
    new_context.remove_value(key)
    return new_context


def get_current() -> Context:
    global _CONTEXT  # pylint: disable=global-statement
    if _CONTEXT is None:
        # FIXME use a better implementation of a configuration manager to avoid having
        # to get configuration values straight from environment variables
        _available_contexts = {}  # typing.Dict[str, Context]

        for entry_point in iter_entry_points("opentelemetry_context"):
            try:
                _available_contexts[entry_point.name] = entry_point.load()  # type: ignore
            except Exception as err:  # pylint: disable=broad-except
                logger.warning(
                    "Could not load entry_point %s:%s", entry_point.name, err
                )

        configured_context = environ.get(
            "OPENTELEMETRY_CONTEXT", "default_context"
        )  # type: str
        _CONTEXT = _available_contexts[configured_context]()  # type: ignore
    return _CONTEXT  # type: ignore


def set_current(context: Context) -> None:
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
