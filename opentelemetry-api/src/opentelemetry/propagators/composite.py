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
from typing import Dict, Optional, Sequence, Set

from opentelemetry.context.context import Context
from opentelemetry.propagators.textmap import TextMapPropagator

_logger = getLogger(__name__)


class CompositeHTTPPropagator(TextMapPropagator):
    """CompositeHTTPPropagator provides a mechanism for combining multiple
    propagators into a single one.

    Args:
        propagators: the list of propagators to use
    """

    def __init__(self, propagators: Sequence[TextMapPropagator]) -> None:
        self._propagators = propagators

    def extract(
        self, carrier: Dict[str, str], context: Optional[Context] = None,
    ) -> Context:
        """Run each of the configured propagators with the given context and
        carrier.
        Propagators are run in the order they are configured, if multiple
        propagators write the same context key, the last propagator that writes
        the context key will override previous propagators.

        See `opentelemetry.propagators.textmap.TextMapPropagator.extract`
        """
        for propagator in self._propagators:
            context = propagator.extract(carrier, context)
        return context  # type: ignore

    def inject(
        self, carrier: Dict[str, str], context: Optional[Context] = None,
    ) -> None:
        """Run each of the configured propagators with the given context and
        carrier. Propagators are run in the order they are configured, if
        multiple propagators write the same carrier key, the last propagator
        that writes the carrier key will override previous propagators.

        See `opentelemetry.propagators.textmap.TextMapPropagator.inject`
        """
        for propagator in self._propagators:
            propagator.inject(carrier, context)

    @property
    def fields(self) -> Set[str]:
        """Returns a set with the fields set in `inject`.

        See
        `opentelemetry.propagators.textmap.TextMapPropagator.fields`
        """
        composite_fields = set()

        for propagator in self._propagators:
            for field in propagator.fields:
                composite_fields.add(field)

        return composite_fields
