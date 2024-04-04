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
# type: ignore

import io
from typing import Generator, Iterable, List
from unittest import TestCase

from opentelemetry.metrics import CallbackOptions, Instrument, Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.measurement import Measurement

# FIXME Test that the instrument methods can be called concurrently safely.


class TestCpuTimeIntegration(TestCase):
    """Integration test of scraping CPU time from proc stat with an observable
    counter"""

    procstat_str = """\
cpu  8549517 4919096 9165935 1430260740 1641349 0 1646147 623279 0 0
cpu0 615029 317746 594601 89126459 129629 0 834346 42137 0 0
cpu1 588232 349185 640492 89156411 124485 0 241004 41862 0 0
intr 4370168813 38 9 0 0 1639 0 0 0 0 0 2865202 0 152 0 0 0 0 0 0 0 0 0 0 0 0 7236812 5966240 4501046 6467792 7289114 6048205 5299600 5178254 4642580 6826812 6880917 6230308 6307699 4699637 6119330 4905094 5644039 4700633 10539029 5365438 6086908 2227906 5094323 9685701 10137610 7739951 7143508 8123281 4968458 5683103 9890878 4466603 0 0 0 8929628 0 5 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
ctxt 6877594077
btime 1631501040
processes 2557351
procs_running 2
procs_blocked 0
softirq 1644603067 0 166540056 208 309152755 8936439 0 1354908 935642970 13 222975718\n"""

    @staticmethod
    def create_measurements_expected(
        instrument: Instrument,
    ) -> List[Measurement]:
        return [
            Measurement(
                6150.29,
                instrument=instrument,
                attributes={"cpu": "cpu0", "state": "user"},
            ),
            Measurement(
                3177.46,
                instrument=instrument,
                attributes={"cpu": "cpu0", "state": "nice"},
            ),
            Measurement(
                5946.01,
                instrument=instrument,
                attributes={"cpu": "cpu0", "state": "system"},
            ),
            Measurement(
                891264.59,
                instrument=instrument,
                attributes={"cpu": "cpu0", "state": "idle"},
            ),
            Measurement(
                1296.29,
                instrument=instrument,
                attributes={"cpu": "cpu0", "state": "iowait"},
            ),
            Measurement(
                0.0,
                instrument=instrument,
                attributes={"cpu": "cpu0", "state": "irq"},
            ),
            Measurement(
                8343.46,
                instrument=instrument,
                attributes={"cpu": "cpu0", "state": "softirq"},
            ),
            Measurement(
                421.37,
                instrument=instrument,
                attributes={"cpu": "cpu0", "state": "guest"},
            ),
            Measurement(
                0,
                instrument=instrument,
                attributes={"cpu": "cpu0", "state": "guest_nice"},
            ),
            Measurement(
                5882.32,
                instrument=instrument,
                attributes={"cpu": "cpu1", "state": "user"},
            ),
            Measurement(
                3491.85,
                instrument=instrument,
                attributes={"cpu": "cpu1", "state": "nice"},
            ),
            Measurement(
                6404.92,
                instrument=instrument,
                attributes={"cpu": "cpu1", "state": "system"},
            ),
            Measurement(
                891564.11,
                instrument=instrument,
                attributes={"cpu": "cpu1", "state": "idle"},
            ),
            Measurement(
                1244.85,
                instrument=instrument,
                attributes={"cpu": "cpu1", "state": "iowait"},
            ),
            Measurement(
                0,
                instrument=instrument,
                attributes={"cpu": "cpu1", "state": "irq"},
            ),
            Measurement(
                2410.04,
                instrument=instrument,
                attributes={"cpu": "cpu1", "state": "softirq"},
            ),
            Measurement(
                418.62,
                instrument=instrument,
                attributes={"cpu": "cpu1", "state": "guest"},
            ),
            Measurement(
                0,
                instrument=instrument,
                attributes={"cpu": "cpu1", "state": "guest_nice"},
            ),
        ]

    def test_cpu_time_callback(self):
        def cpu_time_callback(
            options: CallbackOptions,
        ) -> Iterable[Observation]:
            procstat = io.StringIO(self.procstat_str)
            procstat.readline()  # skip the first line
            for line in procstat:
                if not line.startswith("cpu"):
                    break
                cpu, *states = line.split()
                yield Observation(
                    int(states[0]) / 100, {"cpu": cpu, "state": "user"}
                )
                yield Observation(
                    int(states[1]) / 100, {"cpu": cpu, "state": "nice"}
                )
                yield Observation(
                    int(states[2]) / 100, {"cpu": cpu, "state": "system"}
                )
                yield Observation(
                    int(states[3]) / 100, {"cpu": cpu, "state": "idle"}
                )
                yield Observation(
                    int(states[4]) / 100, {"cpu": cpu, "state": "iowait"}
                )
                yield Observation(
                    int(states[5]) / 100, {"cpu": cpu, "state": "irq"}
                )
                yield Observation(
                    int(states[6]) / 100, {"cpu": cpu, "state": "softirq"}
                )
                yield Observation(
                    int(states[7]) / 100, {"cpu": cpu, "state": "guest"}
                )
                yield Observation(
                    int(states[8]) / 100, {"cpu": cpu, "state": "guest_nice"}
                )

        meter = MeterProvider().get_meter("name")
        observable_counter = meter.create_observable_counter(
            "system.cpu.time",
            callbacks=[cpu_time_callback],
            unit="s",
            description="CPU time",
        )
        measurements = list(observable_counter.callback(CallbackOptions()))
        self.assertEqual(
            measurements, self.create_measurements_expected(observable_counter)
        )

    def test_cpu_time_generator(self):
        def cpu_time_generator() -> (
            Generator[Iterable[Observation], None, None]
        ):
            options = yield
            while True:
                self.assertIsInstance(options, CallbackOptions)
                measurements = []
                procstat = io.StringIO(self.procstat_str)
                procstat.readline()  # skip the first line
                for line in procstat:
                    if not line.startswith("cpu"):
                        break
                    cpu, *states = line.split()
                    measurements.append(
                        Observation(
                            int(states[0]) / 100,
                            {"cpu": cpu, "state": "user"},
                        )
                    )
                    measurements.append(
                        Observation(
                            int(states[1]) / 100,
                            {"cpu": cpu, "state": "nice"},
                        )
                    )
                    measurements.append(
                        Observation(
                            int(states[2]) / 100,
                            {"cpu": cpu, "state": "system"},
                        )
                    )
                    measurements.append(
                        Observation(
                            int(states[3]) / 100,
                            {"cpu": cpu, "state": "idle"},
                        )
                    )
                    measurements.append(
                        Observation(
                            int(states[4]) / 100,
                            {"cpu": cpu, "state": "iowait"},
                        )
                    )
                    measurements.append(
                        Observation(
                            int(states[5]) / 100, {"cpu": cpu, "state": "irq"}
                        )
                    )
                    measurements.append(
                        Observation(
                            int(states[6]) / 100,
                            {"cpu": cpu, "state": "softirq"},
                        )
                    )
                    measurements.append(
                        Observation(
                            int(states[7]) / 100,
                            {"cpu": cpu, "state": "guest"},
                        )
                    )
                    measurements.append(
                        Observation(
                            int(states[8]) / 100,
                            {"cpu": cpu, "state": "guest_nice"},
                        )
                    )
                options = yield measurements

        meter = MeterProvider().get_meter("name")
        observable_counter = meter.create_observable_counter(
            "system.cpu.time",
            callbacks=[cpu_time_generator()],
            unit="s",
            description="CPU time",
        )
        measurements = list(observable_counter.callback(CallbackOptions()))
        self.assertEqual(
            measurements, self.create_measurements_expected(observable_counter)
        )

    maxDiff = None
