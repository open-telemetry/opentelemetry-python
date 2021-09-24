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

# pylint: disable=protected-access

from logging import getLogger
from re import match

_logger = getLogger(__name__)


class View:
    def __init__(
        self,
        instrument_type=None,
        instrument_name=None,
        meter_name=None,
        meter_version=None,
        meter_schema_url=None,
        name=None,
        description=None,
        attribute_keys=None,
        extra_dimensions=None,
        aggregation=None,
        exemplar_reservoir=None,
    ):
        if (
            name
            is instrument_type
            is instrument_name
            is meter_name
            is meter_version
            is meter_schema_url
            is None
        ):
            raise Exception(
                "Some instrument selection criteria must be provided"
            )

        self._instrument_type = instrument_type
        self._instrument_name = instrument_name
        self._meter_name = meter_name
        self._meter_version = meter_version
        self._meter_schema_url = meter_schema_url

        self._name = name

        if self._name is not None:
            if self._instrument_type is not None:
                _logger.warning(
                    "Instrument type matching disabled "
                    "for view with a defined name"
                )
                self._instrument_type = None

            if self._instrument_name is not None:
                _logger.warning(
                    "Instrument name matching disabled "
                    "for view with a defined name"
                )
                self._instrument_name = None

        self._description = description
        self._attribute_keys = attribute_keys
        self._extra_dimensions = extra_dimensions
        self._aggregation = aggregation
        self._exemplar_reservoir = exemplar_reservoir

        self._has_name_and_has_matched = False

    # pylint: disable=too-many-return-statements
    def _match(self, instrument) -> bool:

        if self._has_name_and_has_matched:
            return False

        if self._instrument_type is not None:
            if not isinstance(instrument, self._instrument_type):
                return False

        if self._instrument_name is not None:
            if match(self._instrument_name, instrument.name) is None:
                return False

        if self._meter_name is not None:
            if match(self._meter_name, instrument._meter.name) is None:
                return False

        if self._meter_version is not None:
            if self._meter_version != instrument._meter.version:
                return False

        if self._meter_schema_url is not None:
            if self._meter_schema_url != instrument._meter.schema_url:
                return False

        if self._name is not None:
            self._has_name_and_has_matched = True

        return True
