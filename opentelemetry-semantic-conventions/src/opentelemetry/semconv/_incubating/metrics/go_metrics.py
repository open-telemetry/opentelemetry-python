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


from typing import Final

from opentelemetry.metrics import Counter, Histogram, Meter, UpDownCounter

GO_CONFIG_GOGC: Final = "go.config.gogc"
"""
Heap size target percentage configured by the user, otherwise 100
Instrument: updowncounter
Unit: %
Note: The value range is [0.0,100.0]. Computed from `/gc/gogc:percent`.
"""


def create_go_config_gogc(meter: Meter) -> UpDownCounter:
    """Heap size target percentage configured by the user, otherwise 100"""
    return meter.create_up_down_counter(
        name=GO_CONFIG_GOGC,
        description="Heap size target percentage configured by the user, otherwise 100.",
        unit="%",
    )


GO_GOROUTINE_COUNT: Final = "go.goroutine.count"
"""
Count of live goroutines
Instrument: updowncounter
Unit: {goroutine}
Note: Computed from `/sched/goroutines:goroutines`.
"""


def create_go_goroutine_count(meter: Meter) -> UpDownCounter:
    """Count of live goroutines"""
    return meter.create_up_down_counter(
        name=GO_GOROUTINE_COUNT,
        description="Count of live goroutines.",
        unit="{goroutine}",
    )


GO_MEMORY_ALLOCATED: Final = "go.memory.allocated"
"""
Memory allocated to the heap by the application
Instrument: counter
Unit: By
Note: Computed from `/gc/heap/allocs:bytes`.
"""


def create_go_memory_allocated(meter: Meter) -> Counter:
    """Memory allocated to the heap by the application"""
    return meter.create_counter(
        name=GO_MEMORY_ALLOCATED,
        description="Memory allocated to the heap by the application.",
        unit="By",
    )


GO_MEMORY_ALLOCATIONS: Final = "go.memory.allocations"
"""
Count of allocations to the heap by the application
Instrument: counter
Unit: {allocation}
Note: Computed from `/gc/heap/allocs:objects`.
"""


def create_go_memory_allocations(meter: Meter) -> Counter:
    """Count of allocations to the heap by the application"""
    return meter.create_counter(
        name=GO_MEMORY_ALLOCATIONS,
        description="Count of allocations to the heap by the application.",
        unit="{allocation}",
    )


GO_MEMORY_GC_GOAL: Final = "go.memory.gc.goal"
"""
Heap size target for the end of the GC cycle
Instrument: updowncounter
Unit: By
Note: Computed from `/gc/heap/goal:bytes`.
"""


def create_go_memory_gc_goal(meter: Meter) -> UpDownCounter:
    """Heap size target for the end of the GC cycle"""
    return meter.create_up_down_counter(
        name=GO_MEMORY_GC_GOAL,
        description="Heap size target for the end of the GC cycle.",
        unit="By",
    )


GO_MEMORY_LIMIT: Final = "go.memory.limit"
"""
Go runtime memory limit configured by the user, if a limit exists
Instrument: updowncounter
Unit: By
Note: Computed from `/gc/gomemlimit:bytes`. This metric is excluded if the limit obtained from the Go runtime is math.MaxInt64.
"""


def create_go_memory_limit(meter: Meter) -> UpDownCounter:
    """Go runtime memory limit configured by the user, if a limit exists"""
    return meter.create_up_down_counter(
        name=GO_MEMORY_LIMIT,
        description="Go runtime memory limit configured by the user, if a limit exists.",
        unit="By",
    )


GO_MEMORY_USED: Final = "go.memory.used"
"""
Memory used by the Go runtime
Instrument: updowncounter
Unit: By
Note: Computed from `(/memory/classes/total:bytes - /memory/classes/heap/released:bytes)`.
"""


def create_go_memory_used(meter: Meter) -> UpDownCounter:
    """Memory used by the Go runtime"""
    return meter.create_up_down_counter(
        name=GO_MEMORY_USED,
        description="Memory used by the Go runtime.",
        unit="By",
    )


GO_PROCESSOR_LIMIT: Final = "go.processor.limit"
"""
The number of OS threads that can execute user-level Go code simultaneously
Instrument: updowncounter
Unit: {thread}
Note: Computed from `/sched/gomaxprocs:threads`.
"""


def create_go_processor_limit(meter: Meter) -> UpDownCounter:
    """The number of OS threads that can execute user-level Go code simultaneously"""
    return meter.create_up_down_counter(
        name=GO_PROCESSOR_LIMIT,
        description="The number of OS threads that can execute user-level Go code simultaneously.",
        unit="{thread}",
    )


GO_SCHEDULE_DURATION: Final = "go.schedule.duration"
"""
The time goroutines have spent in the scheduler in a runnable state before actually running
Instrument: histogram
Unit: s
Note: Computed from `/sched/latencies:seconds`. Bucket boundaries are provided by the runtime, and are subject to change.
"""


def create_go_schedule_duration(meter: Meter) -> Histogram:
    """The time goroutines have spent in the scheduler in a runnable state before actually running"""
    return meter.create_histogram(
        name=GO_SCHEDULE_DURATION,
        description="The time goroutines have spent in the scheduler in a runnable state before actually running.",
        unit="s",
    )
