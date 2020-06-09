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

import atexit
import threading

from opentelemetry.context import attach, detach, set_value


class PushController(threading.Thread):
    """A push based controller, used for exporting.

    Uses a worker thread that periodically collects metrics for exporting,
    exports them and performs some post-processing.
    """

    daemon = True

    def __init__(
        self,
        meter_registry,
        exporter,
        interval,
        shutdown_on_exit=True,
    ):
        super().__init__()
        self.meter_registry = meter_registry
        self.exporter = exporter
        self.interval = interval
        self.finished = threading.Event()
        self._atexit_handler = None
        if shutdown_on_exit:
            self._atexit_handler = atexit.register(self.shutdown)
        self.start()

    def run(self):
        while not self.finished.wait(self.interval):
            # Only run if meters exist
            if self.meter_registry:
                self.tick()

    def shutdown(self):
        self.finished.set()
        # Run one more collection pass to flush metrics batched in the meter
        self.tick()
        self.exporter.shutdown()
        if self._atexit_handler is not None:
            atexit.unregister(self._atexit_handler)
            self._atexit_handler = None

    def tick(self):
        # Collect all of the meter's metrics to be exported
        token = attach(set_value("suppress_instrumentation", True))
        for meter in self.meter_registry.values():
            meter.collect()
            # Export the collected metrics
            self.exporter.export(meter.batcher.checkpoint_set())
            # Perform post-exporting logic
            meter.batcher.finished_collection()
        detach(token)
