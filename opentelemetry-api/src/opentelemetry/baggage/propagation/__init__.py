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
from urllib.parse import quote_plus, unquote_plus

from logging import getLogger
from re import compile, split
from typing import Iterable, Mapping, Optional, Set

from opentelemetry.baggage import get_all, set_baggage, _is_valid_pair
from opentelemetry.context import get_current
from opentelemetry.context.context import Context
from opentelemetry.util.re import _DELIMITER_PATTERN
from opentelemetry.propagators import textmap

_logger = getLogger(__name__)


class W3CBaggagePropagator(textmap.TextMapPropagator):
    """Extracts and injects Baggage which is used to annotate telemetry."""

    _MAX_HEADER_LENGTH = 8192
    _MAX_PAIR_LENGTH = 4096
    _MAX_PAIRS = 180
    _BAGGAGE_HEADER_NAME = "baggage"

    def extract(
        self,
        carrier: textmap.CarrierT,
        context: Optional[Context] = None,
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
            _logger.warning(
                "Baggage header `%s` exceeded the maximum number of bytes per baggage-string.",
                header,
            )
            return context

        baggage_entries = split(_DELIMITER_PATTERN, header)

        if len(baggage_entries) > self._MAX_PAIRS:
            _logger.warning(
                "Baggage header `%s` exceeded the maximum number of list-members",
                header,
            )
            return context

        entries = []
        for entry in baggage_entries:
            if len(entry) > self._MAX_PAIR_LENGTH:
                _logger.warning(
                    "Baggage entry `%s` exceeded the maximum number of bytes per list-member",
                    entry,
                )
                return context
            if not entry:  # empty string
                continue
            try:
                name, value = entry.split("=", 1)
            except Exception:  # pylint: disable=broad-except
                _logger.warning(
                    "Baggage list-member doesn't match the format: `%s`", entry
                )
                return context
            name = unquote_plus(name).strip().lower()
            value = unquote_plus(value).strip()
            if not _is_valid_pair(name, value):
                _logger.warning("Invalid baggage entry: `%s`", entry)
                return context

            entries.append((name, value))

        for name, value in entries:
            context = set_baggage(
                name,
                value,
                context=context,
            )

        return context  # type: ignore

    def inject(
        self,
        carrier: textmap.CarrierT,
        context: Optional[Context] = None,
        setter: textmap.Setter = textmap.default_setter,
    ) -> None:
        """Injects Baggage into the carrier.

        See
        `opentelemetry.propagators.textmap.TextMapPropagator.inject`
        """
        baggage_entries = get_all(context=context)
        if not baggage_entries:
            return

        baggage_string = _format_baggage(baggage_entries)
        setter.set(carrier, self._BAGGAGE_HEADER_NAME, baggage_string)

    @property
    def fields(self) -> Set[str]:
        """Returns a set with the fields set in `inject`."""
        return {self._BAGGAGE_HEADER_NAME}


def _format_baggage(baggage_entries: Mapping[str, object]) -> str:

    key_values = []
    for key, value in baggage_entries.items():
        key_values.append(quote_plus(str(key)) + "=" + quote_plus(str(value)))

    return ",".join(key_values)


def _extract_first_element(
    items: Optional[Iterable[textmap.CarrierT]],
) -> Optional[textmap.CarrierT]:
    if items is None:
        return None
    return next(iter(items), None)
