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

import threading

from opentelemetry.context import attach, detach, set_value
from opentelemetry.metrics import Meter
from opentelemetry.sdk.metrics.export import MetricsExporter


class PushController(threading.Thread):
    """A push based controller, used for collecting and exporting.

    Uses a worker thread that periodically collects metrics for exporting,
    exports them and performs some post-processing.

    Args:
        meter: The meter used to collect metrics.
        exporter: The exporter used to export metrics.
        interval: The collect/export interval in seconds.
    """

    daemon = True

    def __init__(
        self, meter: Meter, exporter: MetricsExporter, interval: float
    ):
        super().__init__()
        self.meter = meter
        self.exporter = exporter
        self.interval = interval
        self.finished = threading.Event()
        self.start()

    def run(self):
        while not self.finished.wait(self.interval):
            self.tick()

    def shutdown(self):
        self.finished.set()
        # Run one more collection pass to flush metrics batched in the meter
        self.tick()

    def tick(self):
        # Collect all of the meter's metrics to be exported
        self.meter.collect()
        # Export the collected metrics
        token = attach(set_value("suppress_instrumentation", True))
        self.exporter.export(self.meter.batcher.checkpoint_set())
        detach(token)
        # Perform post-exporting logic
        self.meter.batcher.finished_collection()
