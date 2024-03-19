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

import time

from oteltest import OtelTest, Telemetry

from opentelemetry import trace

SERVICE_NAME = "my-otel-test"
NUM_ADDS = 12

if __name__ == "__main__":
    tracer = trace.get_tracer("my-tracer")
    for i in range(NUM_ADDS):
        with tracer.start_as_current_span("my-span"):
            print(f"simple_loop.py: {i+1}/{NUM_ADDS}")
            time.sleep(0.5)


class MyOtelTest(OtelTest):
    def requirements(self):
        return "opentelemetry-distro", "opentelemetry-exporter-otlp-proto-grpc"

    def environment_variables(self):
        return {"OTEL_SERVICE_NAME": SERVICE_NAME}

    def wrapper_command(self):
        return "opentelemetry-instrument"

    def on_start(self):
        return None

    def on_stop(
        self, telemetry: Telemetry, stdout: str, stderr: str, returncode: int
    ) -> None:
        assert telemetry.num_spans() == NUM_ADDS
