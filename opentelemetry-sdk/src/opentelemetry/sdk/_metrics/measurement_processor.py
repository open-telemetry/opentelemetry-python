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
from typing import Mapping

from opentelemetry._metrics.instrument import Instrument
from opentelemetry.sdk._metrics.measurement import Measurement
from opentelemetry.sdk._metrics.metric_reader import MetricReader


class _MeasurementProcessor(ABC):
    # FIXME There is a design intention to support other MeasurementProcessors.
    # In that case there must be a mechanism for the user to select the
    # MeasurementProcessor.

    @abstractmethod
    def process(
        self, instrument: Instrument, measurement: Measurement
    ) -> None:
        # FIXME this may be code smell a process method on a
        # MeasurementProcessor class should receive a measurement as argument
        # not a measurement and an instrument. An intention to minimize lock
        # impact on the metrics SDK performance may be the reason behind this.
        pass


class _SequentialMeasurementProcessor(_MeasurementProcessor):
    def __init__(self, meter_provider):

        self._meter_provider = meter_provider
        self._instrument_metric_reader: Mapping[Instrument, MetricReader] = {}

    def process(
        self, instrument: Instrument, measurement: Measurement
    ) -> None:

        # pylint: disable=protected-access
        for metric_reader in self._meter_provider._metric_readers:

            # FIXME this may be a code smell, the process method is not part of
            # the MetricReader API. The main point is that a method of a
            # MetricReader is being called when doing measurement processing
            # instead of measurement collection.
            metric_reader._process(instrument, measurement)
