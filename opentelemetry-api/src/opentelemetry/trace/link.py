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

from abc import ABC, abstractmethod

from opentelemetry.attributes import BoundedAttributes
from opentelemetry.trace.span import SpanContext
from opentelemetry.util import types


class _LinkBase(ABC):
    def __init__(self, context: SpanContext) -> None:
        self._context = context

    @property
    def context(self) -> SpanContext:
        return self._context

    @property
    @abstractmethod
    def attributes(self) -> types.Attributes:
        pass


class Link(_LinkBase):
    """A link to a `Span`. The attributes of a Link are immutable.

    Args:
        context: `SpanContext` of the `Span` to link to.
        attributes: Link's attributes.
    """

    def __init__(
        self,
        context: SpanContext,
        attributes: types.Attributes = None,
    ) -> None:
        super().__init__(context)
        self._attributes = attributes

    @property
    def attributes(self) -> types.Attributes:
        return self._attributes

    @property
    def dropped_attributes(self) -> int:
        if isinstance(self._attributes, BoundedAttributes):
            return self._attributes.dropped
        return 0
