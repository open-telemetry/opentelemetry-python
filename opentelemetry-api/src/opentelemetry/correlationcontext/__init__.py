# Copyright 2020, OpenTelemetry Authors
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
import itertools
import string
import typing
from contextlib import contextmanager

from opentelemetry.context import attach, get_value, set_value
from opentelemetry.context.context import Context

CORRELATION_CONTEXT_KEY = "correlation-context"


class CorrelationContext(abc.ABC):
    """A container for correlation context"""

    @abc.abstractmethod
    def get_correlations(self, context: typing.Optional[Context] = None):
        """ Returns the name/value pairs in the CorrelationContext
        
        Args:
            context: the Context to use. If not set, uses current Context

        Returns:
            name/value pairs in the CorrelationContext
        """

    @abc.abstractmethod
    def get_correlation(
        self, name, context: typing.Optional[Context] = None
    ) -> typing.Optional[object]:
        """ Provides access to the value for a name/value pair by a prior event
        
        Args:
            name: the name of the value to retrieve
            context: the Context to use. If not set, uses current Context

        Returns:
            the value associated with the given name, or null if the given name is
            not present.
        """

    @abc.abstractmethod
    def set_correlation(
        self, name, value, context: typing.Optional[Context] = None
    ) -> Context:
        """

        Args:
            name: the name of the value to set
            value: the value to set
            context: the Context to use. If not set, uses current Context

        Returns:
            a Context with the value updated
        """

    @abc.abstractmethod
    def remove_correlation(
        self, name, context: typing.Optional[Context] = None
    ) -> Context:
        """

        Args:
            name: the name of the value to remove
            context: the Context to use. If not set, uses current Context

        Returns:
            a Context with the name/value removed
        """

    @abc.abstractmethod
    def clear_correlations(
        self, context: typing.Optional[Context] = None
    ) -> Context:
        """
        Args:
            context: the Context to use. If not set, uses current Context

        Returns:
            a Context with all correlations removed
        """


class DefaultCorrelationContext(CorrelationContext):
    """ Default no-op implementation of CorrelationContext """

    def get_correlations(
        self, context: typing.Optional[Context] = None
    ) -> typing.Dict:
        return {}

    def get_correlation(
        self, name, context: typing.Optional[Context] = None
    ) -> typing.Optional[object]:
        return None

    def set_correlation(
        self, name, value, context: typing.Optional[Context] = None
    ) -> Context:
        return context

    def remove_correlation(
        self, name, context: typing.Optional[Context] = None
    ) -> Context:
        return context

    def clear_correlations(
        self, context: typing.Optional[Context] = None
    ) -> Context:
        return context
