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

import threading


class PushController(threading.Thread):
    """A push based controller, used for exporting.

    Uses a worker thread that periodically collects metrics for exporting,
    exports them and performs some post-processing.
    """

    def __init__(self, meter, exporter, interval):
        super().__init__()
        self.meter = meter
        self.exporter = exporter
        self.interval = interval
        self.finished = threading.Event()
        self.start()

    def run(self):
        while not self.finished.wait(self.interval):
            self.tick()

    def cancel(self):
        self.finished.set()

    def tick(self):
        # Collect all of the meter's metrics to be exported
        self.meter.collect()
        # Export the given metrics in the batcher
        self.exporter.export(self.meter.batcher.check_point_set())
        # Perform post-exporting logic based on batcher configuration
        self.meter.batcher.finished_collection()
