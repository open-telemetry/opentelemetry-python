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

from typing import Dict, Optional, Set
from urllib.parse import quote_plus, unquote

from opentelemetry import baggage
from opentelemetry.context import get_current
from opentelemetry.context.context import Context
from opentelemetry.propagators.textmap import TextMapPropagator


class W3CBaggagePropagator(TextMapPropagator):
    """Extracts and injects Baggage which is used to annotate telemetry."""

    _baggage_header_name = "baggage"
    _max_header_length = 9182
    _max_pairs = 180
    _max_pair_length = 4096

    def extract(
        self, carrier: Dict[str, str], context: Optional[Context] = None,
    ) -> Context:
        """Extract Baggage from the carrier.

        See
        `opentelemetry.propagators.textmap.TextMapPropagator.extract`
        """

        if context is None:
            context = get_current()

        header = carrier.get(self._baggage_header_name)

        if header is None or len(header) > self._max_header_length:
            return context

        total_baggage_entries = self._max_pairs

        for entry in header.split(","):
            if total_baggage_entries <= 0:
                return context
            total_baggage_entries -= 1
            if len(entry) > self._max_pair_length:
                continue
            if "=" in entry:
                name, value = entry.split("=", 1)
                context = baggage.set_baggage(
                    unquote(name).strip(),
                    unquote(value).strip(),
                    context=context,
                )

        return context

    def inject(
        self, carrier: Dict[str, str], context: Optional[Context] = None,
    ) -> None:
        """Injects Baggage into the carrier.

        See
        `opentelemetry.propagators.textmap.TextMapPropagator.inject`
        """
        baggage_entries = baggage.get_all(context=context)

        if baggage_entries:
            carrier[self._baggage_header_name] = ",".join(
                key + "=" + quote_plus(str(value))
                for key, value in baggage_entries.items()
            )

    @property
    def fields(self) -> Set[str]:
        """Returns a set with the fields set in `inject`."""
        return {self._baggage_header_name}
