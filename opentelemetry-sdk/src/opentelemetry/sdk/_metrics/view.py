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
from typing import Optional, Set, Type

from opentelemetry._metrics.instrument import Instrument
from opentelemetry.sdk._metrics.aggregation import Aggregation

_logger = getLogger(__name__)


class View:
    def __init__(
        self,
        instrument_type: Optional[Type[Instrument]] = None,
        instrument_name: Optional[str] = None,
        meter_name: Optional[str] = None,
        meter_version: Optional[str] = None,
        meter_schema_url: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        attribute_keys: Set[str] = None,
        aggregation: Optional[Type[Aggregation]] = None,
    ):
        """
        An instance of `View` is an object that can perform two actions:

        1. Match instruments: When an instrument matches a view, measurements
           received by that instrument will be processed.
        2. Customize metric streams: A metric stream is identified by a match
           between a view and an instrument and a set of attributes. The metric
           stream can be customized by certain attributes of the corresponding
           view.

        The attributes documented next serve one of the previous two purposes.

        Args:
            instrument_type: This is an instrument matching attribute: the class
            the instrument must be to match the view.
            instrument_name: This is an instrument matching attribute: the name
            the instrument must have to match the view.
            meter_name: This is an instrument matching attribute: the name
            the instrument meter must have to match the view.
            meter_version : This is an instrument matching attribute: the
            version the instrument meter must have to match the view.
            meter_schema URL : This is an instrument matching attribute: the
            schema URL the instrument meter must have to match the view.
            name: This is a metric stream customizing attribute: the name of
            the metric stream. If `None`, the name of the instrument will be
            used.
            description: This is a metric stream customizing attribute: the
            description of the metric stream. If `None`, the description of the
            instrument will be used.
            attribute_keys: This is a metric stream customizing attribute: this
            is a set of attribute keys. If not `None` then only the measurement
            attributes that are in `attribute_keys` will be used to identify
            the metric stream.
            aggregation: This is a metric stream customizing attribute: every
            metric stream has an aggregation instance, this is the class of
            aggregation this instance will be. If `None` the default
            aggregation class of the instrument will be used.
        """

        if (
            instrument_type
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

            if self._meter_name is not None:
                _logger.warning(
                    "Instrument meter name matching disabled "
                    "for view with a defined name"
                )
                self._meter_name = None

            if self._meter_version is not None:
                _logger.warning(
                    "Instrument meter version matching disabled "
                    "for view with a defined version"
                )
                self._meter_version = None

            if self._meter_schema_url is not None:
                _logger.warning(
                    "Instrument meter schema URL matching disabled "
                    "for view with a defined version"
                )
                self._meter_schema_url = None

        self._description = description
        self._attribute_keys = attribute_keys
        self._aggregation = aggregation

        self._has_name_and_has_matched = False

    # pylint: disable=too-many-return-statements
    def _match(self, instrument: Instrument) -> bool:

        if self._has_name_and_has_matched:
            return False

        if self._instrument_type is not None:
            if not isinstance(instrument, self._instrument_type):
                return False

        if self._instrument_name is not None:
            if self._instrument_name != instrument.name:
                return False

        if self._meter_name is not None:
            # pylint: disable=protected-access
            if self._meter_name != instrument._meter.name:
                return False

        if self._meter_version is not None:
            # pylint: disable=protected-access
            if self._meter_version != instrument._meter.version:
                return False

        if self._meter_schema_url is not None:
            # pylint: disable=protected-access
            if self._meter_schema_url != instrument._meter.schema_url:
                return False

        if self._name is not None:
            self._has_name_and_has_matched = True

        return True
