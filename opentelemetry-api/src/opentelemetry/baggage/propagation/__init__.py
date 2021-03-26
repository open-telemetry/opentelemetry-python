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
#
import typing
import urllib.parse

from opentelemetry import baggage
from opentelemetry.context import get_current
from opentelemetry.context.context import Context
from opentelemetry.propagators import textmap


class W3CBaggagePropagator(textmap.TextMapPropagator):
    """Extracts and injects Baggage which is used to annotate telemetry."""

    _MAX_HEADER_LENGTH = 8192
    _MAX_PAIR_LENGTH = 4096
    _MAX_PAIRS = 180
    _BAGGAGE_HEADER_NAME = "baggage"

    def extract(
        self,
        carrier: textmap.CarrierT,
        context: typing.Optional[Context] = None,
        getter: textmap.Getter = textmap.default_getter,
    ) -> Context:
        """Extract Baggage from the carrier.

        See
        `opentelemetry.propagators.textmap.TextMapPropagator.extract`
        """

        if context is None:
            context = get_current()

        header = _extract_first_element(
            getter.get(carrier, self._BAGGAGE_HEADER_NAME)
        )

        if not header or len(header) > self._MAX_HEADER_LENGTH:
            return context

        baggage_entries = header.split(",")
        total_baggage_entries = self._MAX_PAIRS
        for entry in baggage_entries:
            if total_baggage_entries <= 0:
                return context
            total_baggage_entries -= 1
            if len(entry) > self._MAX_PAIR_LENGTH:
                continue
            try:
                name, value = entry.split("=", 1)
            except Exception:  # pylint: disable=broad-except
                continue
            context = baggage.set_baggage(
                urllib.parse.unquote(name).strip(),
                urllib.parse.unquote(value).strip(),
                context=context,
            )

        return context

    def inject(
        self,
        carrier: textmap.CarrierT,
        context: typing.Optional[Context] = None,
        setter: textmap.Setter = textmap.default_setter,
    ) -> None:
        """Injects Baggage into the carrier.

        See
        `opentelemetry.propagators.textmap.TextMapPropagator.inject`
        """
        baggage_entries = baggage.get_all(context=context)
        if not baggage_entries:
            return

        baggage_string = _format_baggage(baggage_entries)
        setter.set(carrier, self._BAGGAGE_HEADER_NAME, baggage_string)

    @property
    def fields(self) -> typing.Set[str]:
        """Returns a set with the fields set in `inject`."""
        return {self._BAGGAGE_HEADER_NAME}


def _format_baggage(baggage_entries: typing.Mapping[str, object]) -> str:
    return ",".join(
        key + "=" + urllib.parse.quote_plus(str(value))
        for key, value in baggage_entries.items()
    )


def _extract_first_element(
    items: typing.Optional[typing.Iterable[textmap.CarrierT]],
) -> typing.Optional[textmap.CarrierT]:
    if items is None:
        return None
    return next(iter(items), None)
