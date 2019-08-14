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

import typing


class CounterTimeSeries:

    def add(self, value: typing.Union[float, int]) -> None:
        """Adds the given value to the current value. Cannot be negative."""

    def set(self, value: typing.Union[float, int]) -> None:
        """Sets the current value to the given value.

        The given value must be larger than the current recorded value.
        """


class GaugeTimeSeries:

    def set(self, value: typing.Union[float, int]) -> None:
        """Sets the current value to the given value. Can be negative."""


class MeasureTimeSeries:

    def record(self, value: typing.Union[float, int]) -> None:
        """Records the given value to this measure.

        Logic depends on type of aggregation used for this measure.
        """
   