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

# pylint: disable=unused-import

import os
from abc import ABC, abstractmethod
from threading import Lock
from time import time_ns
from typing import Iterable, List, Mapping, Optional

# This kind of import is needed to avoid Sphinx errors.
import opentelemetry.sdk.metrics
import opentelemetry.sdk.metrics._internal.instrument
import opentelemetry.sdk.metrics._internal.sdk_configuration
from opentelemetry.metrics._internal.instrument import CallbackOptions
from opentelemetry.sdk.metrics._internal.exceptions import MetricsTimeoutError
from opentelemetry.sdk.metrics._internal.measurement import Measurement
from opentelemetry.sdk.metrics._internal.metric_reader_storage import (
    MetricReaderStorage,
)
from opentelemetry.sdk.metrics._internal.point import Metric


class MeasurementConsumer(ABC):
    @abstractmethod
    def consume_measurement(self, measurement: Measurement) -> None:
        pass

    @abstractmethod
    def register_asynchronous_instrument(
        self,
        instrument: (
            "opentelemetry.sdk.metrics._internal.instrument_Asynchronous"
        ),
    ):
        pass

    @abstractmethod
    def collect(
        self,
        metric_reader: "opentelemetry.sdk.metrics.MetricReader",
        timeout_millis: float = 10_000,
    ) -> Optional[Iterable[Metric]]:
        pass


class SynchronousMeasurementConsumer(MeasurementConsumer):
    def __init__(
        self,
        sdk_config: "opentelemetry.sdk.metrics._internal.SdkConfiguration",
    ) -> None:
        self._lock = Lock()
        self._sdk_config = sdk_config
        # should never be mutated
        self._reader_storages: Mapping[
            "opentelemetry.sdk.metrics.MetricReader", MetricReaderStorage
        ] = {
            reader: MetricReaderStorage(
                sdk_config,
                reader._instrument_class_temporality,
                reader._instrument_class_aggregation,
            )
            for reader in sdk_config.metric_readers
        }
        self._async_instruments: List[
            "opentelemetry.sdk.metrics._internal.instrument._Asynchronous"
        ] = []
        if hasattr(os, "register_at_fork"):
            os.register_at_fork(
                after_in_child=self._at_fork_reinit
            )  # pylint: disable=protected-access

    def _at_fork_reinit(self):
        """Reinitialize lock in child process after fork"""
        self._lock._at_fork_reinit()
        # Lazy reinitialization of storages on first use post fork. This is
        # done to avoid the overhead of reinitializing the storages on
        # every fork.
        self._needs_storage_reinit = True
        self._async_instruments.clear()

    def consume_measurement(self, measurement: Measurement) -> None:
        if getattr(self, '_needs_storage_reinit', False):
            self._reinit_storages()
            self._needs_storage_reinit = False

        should_sample_exemplar = (
            self._sdk_config.exemplar_filter.should_sample(
                measurement.value,
                measurement.time_unix_nano,
                measurement.attributes,
                measurement.context,
            )
        )
        for reader_storage in self._reader_storages.values():
            reader_storage.consume_measurement(
                measurement, should_sample_exemplar
            )

    def register_asynchronous_instrument(
        self,
        instrument: (
            "opentelemetry.sdk.metrics._internal.instrument._Asynchronous"
        ),
    ) -> None:
        with self._lock:
            self._async_instruments.append(instrument)

    def collect(
        self,
        metric_reader: "opentelemetry.sdk.metrics.MetricReader",
        timeout_millis: float = 10_000,
    ) -> Optional[Iterable[Metric]]:

        if getattr(self, '_needs_storage_reinit', False):
            self._reinit_storages()
            self._needs_storage_reinit = False

        with self._lock:
            metric_reader_storage = self._reader_storages[metric_reader]
            # for now, just use the defaults
            callback_options = CallbackOptions()
            deadline_ns = time_ns() + (timeout_millis * 1e6)

            default_timeout_ns = 10000 * 1e6

            for async_instrument in self._async_instruments:
                remaining_time = deadline_ns - time_ns()

                if remaining_time < default_timeout_ns:
                    callback_options = CallbackOptions(
                        timeout_millis=remaining_time / 1e6
                    )

                measurements = async_instrument.callback(callback_options)
                if time_ns() >= deadline_ns:
                    raise MetricsTimeoutError(
                        "Timed out while executing callback"
                    )

                for measurement in measurements:
                    should_sample_exemplar = (
                        self._sdk_config.exemplar_filter.should_sample(
                            measurement.value,
                            measurement.time_unix_nano,
                            measurement.attributes,
                            measurement.context,
                        )
                    )
                    metric_reader_storage.consume_measurement(
                        measurement, should_sample_exemplar
                    )

            result = self._reader_storages[metric_reader].collect()

        return result

    def _reinit_storages(self):
        # Reinitialize the storages. Use to reinitialize the storages after a
        # fork to avoid duplicate data points.
        with self._lock:
            for storage in self._reader_storages.values():
                storage._lock._at_fork_reinit()
                storage._instrument_view_instrument_matches.clear()
