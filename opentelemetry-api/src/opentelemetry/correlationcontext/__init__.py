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

import copy
import itertools
import string
import typing
from contextlib import contextmanager

from opentelemetry.context import ContextAPI

CORRELATION_CONTEXT_KEY = "correlation-context-key"


class CorrelationContextManager:
    """
    Manages access to CorrelationContext entries
    """

    def __init__(
        self, entries: typing.Optional[typing.Dict[str, typing.Any]] = None
    ) -> None:
        if entries:
            self._correlation_context = copy.deepcopy(entries)
        else:
            self._correlation_context = {}

    def get_correlations(self) -> typing.Dict:
        """
        Returns the entries in this CorrelationContext. The order of entries is not significant. Based
        on the languagespecification, the returned value can be either an immutable collection or an
        immutable iterator to the collection of entries in this CorrelationContext.

        Returns:
            An immutable iterator to the collection of entries in this CorrelationContext
        """
        return self._correlation_context.items()

    def get_correlation(
        self, context: ContextAPI, name: str
    ) -> typing.Optional[typing.Any]:
        """
        To access the value for an entry by a prior event, the Correlations API provides a
        function which takes a context and a name as input, and returns a value. Returns
        the Value associated with the given Name, or null if the given Name is not present.

        Args:
            context: The context in which to find the CorrelationContext
            name: The name of the entry to retrieve
        Returns:
            The value of the entry matching the name
        """
        # pylint: disable=no-self-use
        correlation_context = context.get_value(CORRELATION_CONTEXT_KEY)
        if correlation_context and name in correlation_context:
            return correlation_context[name]
        return None

    def set_correlation(
        self, context: ContextAPI, name: str, value: typing.Any
    ) -> ContextAPI:
        """
        To record the value for an entry, the Correlations API provides a function which takes a
        context, a name, and a value as input. Returns an updated Context which contains the new value.

        Args:
            context: The context in which to find the CorrelationContext
            name: The name of the entry to set
            value: The value of the entry
        Returns:
            A new Context object with updated correlations
        """
        new_correlation_context = self._copy()
        new_correlation_context[name] = value
        return context.set_value(
            CORRELATION_CONTEXT_KEY, new_correlation_context
        )

    def remove_correlation(self, context: ContextAPI, name: str) -> ContextAPI:
        """
        To delete an entry, the Correlations API provides a function which takes a context and a name as
        input. Returns an updated Context which no longer contains the selected Name.

        Args:
            context: The context in which to remove the CorrelationContext
            name: The name of the entry to remove
        Returns:
            A new Context object with the correlation removed
        """
        new_correlation_context = self._copy()
        if name in new_correlation_context:
            del new_correlation_context[name]
        return context.set_value(
            CORRELATION_CONTEXT_KEY, new_correlation_context
        )

    def clear_correlations(self, context: ContextAPI) -> ContextAPI:
        """
        To avoid sending any entries to an untrusted process, the Correlation API provides a function
        to remove all Correlations from a context. Returns an updated Context with no correlations.

        Args:
            context: The context in which to clear the CorrelationContext
        Returns:
            A new Context object with no correlations
        """
        # pylint: disable=no-self-use
        return context.set_value(CORRELATION_CONTEXT_KEY, {})

    def _copy(self) -> typing.Dict[str, typing.Any]:
        """
        Helper function to abstract the mechanism used to copy CorrelationContext values

        Returns:
            A copy of the current entries in the CorrelationContext
        """
        return copy.deepcopy(self._correlation_context)
