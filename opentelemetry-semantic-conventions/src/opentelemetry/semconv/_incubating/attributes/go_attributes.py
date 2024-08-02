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

GO_MEMORY_TYPE: Final = "go.memory.type"
"""
The type of memory.
"""


class GoMemoryTypeValues(Enum):
    STACK = "stack"
    """Memory allocated from the heap that is reserved for stack space, whether or not it is currently in-use."""
    OTHER = "other"
    """Memory used by the Go runtime, excluding other categories of memory usage described in this enumeration."""
