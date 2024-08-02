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

from enum import Enum
from typing import Final

V8JS_GC_TYPE: Final = "v8js.gc.type"
"""
The type of garbage collection.
"""

V8JS_HEAP_SPACE_NAME: Final = "v8js.heap.space.name"
"""
The name of the space type of heap memory.
Note: Value can be retrieved from value `space_name` of [`v8.getHeapSpaceStatistics()`](https://nodejs.org/api/v8.html#v8getheapspacestatistics).
"""


class V8jsGcTypeValues(Enum):
    MAJOR = "major"
    """Major (Mark Sweep Compact)."""
    MINOR = "minor"
    """Minor (Scavenge)."""
    INCREMENTAL = "incremental"
    """Incremental (Incremental Marking)."""
    WEAKCB = "weakcb"
    """Weak Callbacks (Process Weak Callbacks)."""


class V8jsHeapSpaceNameValues(Enum):
    NEW_SPACE = "new_space"
    """New memory space."""
    OLD_SPACE = "old_space"
    """Old memory space."""
    CODE_SPACE = "code_space"
    """Code memory space."""
    MAP_SPACE = "map_space"
    """Map memory space."""
    LARGE_OBJECT_SPACE = "large_object_space"
    """Large object memory space."""
