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

from opentelemetry.metrics import Histogram, Meter, UpDownCounter

V8JS_GC_DURATION: Final = "v8js.gc.duration"
"""
Garbage collection duration
Instrument: histogram
Unit: s
Note: The values can be retrieve from [`perf_hooks.PerformanceObserver(...).observe({ entryTypes: ['gc'] })`](https://nodejs.org/api/perf_hooks.html#performanceobserverobserveoptions).
"""


def create_v8js_gc_duration(meter: Meter) -> Histogram:
    """Garbage collection duration"""
    return meter.create_histogram(
        name=V8JS_GC_DURATION,
        description="Garbage collection duration.",
        unit="s",
    )


V8JS_HEAP_SPACE_AVAILABLE_SIZE: Final = "v8js.heap.space.available_size"
"""
Heap space available size
Instrument: updowncounter
Unit: By
Note: Value can be retrieved from value `space_available_size` of [`v8.getHeapSpaceStatistics()`](https://nodejs.org/api/v8.html#v8getheapspacestatistics).
"""


def create_v8js_heap_space_available_size(meter: Meter) -> UpDownCounter:
    """Heap space available size"""
    return meter.create_up_down_counter(
        name=V8JS_HEAP_SPACE_AVAILABLE_SIZE,
        description="Heap space available size.",
        unit="By",
    )


V8JS_HEAP_SPACE_PHYSICAL_SIZE: Final = "v8js.heap.space.physical_size"
"""
Committed size of a heap space
Instrument: updowncounter
Unit: By
Note: Value can be retrieved from value `physical_space_size` of [`v8.getHeapSpaceStatistics()`](https://nodejs.org/api/v8.html#v8getheapspacestatistics).
"""


def create_v8js_heap_space_physical_size(meter: Meter) -> UpDownCounter:
    """Committed size of a heap space"""
    return meter.create_up_down_counter(
        name=V8JS_HEAP_SPACE_PHYSICAL_SIZE,
        description="Committed size of a heap space.",
        unit="By",
    )


V8JS_MEMORY_HEAP_LIMIT: Final = "v8js.memory.heap.limit"
"""
Total heap memory size pre-allocated
Instrument: updowncounter
Unit: By
Note: The value can be retrieved from value `space_size` of [`v8.getHeapSpaceStatistics()`](https://nodejs.org/api/v8.html#v8getheapspacestatistics).
"""


def create_v8js_memory_heap_limit(meter: Meter) -> UpDownCounter:
    """Total heap memory size pre-allocated"""
    return meter.create_up_down_counter(
        name=V8JS_MEMORY_HEAP_LIMIT,
        description="Total heap memory size pre-allocated.",
        unit="By",
    )


V8JS_MEMORY_HEAP_USED: Final = "v8js.memory.heap.used"
"""
Heap Memory size allocated
Instrument: updowncounter
Unit: By
Note: The value can be retrieved from value `space_used_size` of [`v8.getHeapSpaceStatistics()`](https://nodejs.org/api/v8.html#v8getheapspacestatistics).
"""


def create_v8js_memory_heap_used(meter: Meter) -> UpDownCounter:
    """Heap Memory size allocated"""
    return meter.create_up_down_counter(
        name=V8JS_MEMORY_HEAP_USED,
        description="Heap Memory size allocated.",
        unit="By",
    )
