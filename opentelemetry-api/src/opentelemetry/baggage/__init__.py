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

from typing import Tuple
from opentelemetry.context import Context

from opentelemetry.context.propagation import (
    HTTPExtractor,
    HTTPInjector,
)

#     # INVALID_HTTP_EXTRACTOR,
#     # INVALID_HTTP_INJECTOR,
# )


EMPTY_VALUE = ""
INVALID_CONTEXT = Context


class BaggageManager:
    """ TODO """

    def set_value(self, ctx: Context, key: str, value: str) -> Context:
        """
        Sets a value on a Context

        Args:
            ctx: Context to modify
            key: Key of the value to set
            value: Value used to update the context

        Return:
            Context: Updated context
        """
        # pylint: disable=unused-argument
        return ctx

    def value(self, ctx: Context, key: str) -> str:
        """
        Gets a value on a Context

        Args:
            ctx: Context to query
            key: Key of the value to get

        Return:
            str: Value of the key
        """
        # pylint: disable=unused-argument
        return EMPTY_VALUE

    def remove_value(self, ctx: Context, key: str) -> Context:
        """ TODO """
        # pylint: disable=unused-argument
        return INVALID_CONTEXT

    def clear(self, ctx: Context) -> Context:
        """ TODO """
        # pylint: disable=unused-argument
        return INVALID_CONTEXT

    @classmethod
    def http_propagator(cls) -> Tuple[HTTPExtractor, HTTPInjector]:
        """ TODO """
        return (HTTPExtractor, HTTPInjector)

