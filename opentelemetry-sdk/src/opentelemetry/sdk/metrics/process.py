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

from threading import Thread
from time import sleep

from ABC import abstractmethod


class Process(Thread):
    def __init__(
        self, meter, views, measurement_processors, metric_processors, exporter
    ):
        self._meter = meter
        self._views = views
        self._measurement_processors = measurement_processors
        self._metric_processors = metric_processors
        self._exporter = exporter

    @abstractmethod
    def stop(self, timeout=None):
        pass

    def _process(self):
        self._meter.collect_measurements()


class IntervalProcess(Process):
    def __init__(self, meter, instruments, interval, exporter):
        super().__init__(meter, instruments)
        self._interval = interval
        self._stopped = False

    def run(self):
        while not self._shutdown:
            sleep(self._interval)
            self._exporter.export()

    def stop(self, timeout=None):
        self._stopped = True
        self.join(timeout=timeout)
