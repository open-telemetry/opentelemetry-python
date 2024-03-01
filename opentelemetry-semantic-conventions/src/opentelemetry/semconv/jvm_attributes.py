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

# pylint: disable=too-many-lines

from enum import Enum


JVM_GC_ACTION = "jvm.gc.action"
"""
Name of the garbage collector action.
Note: Garbage collector action is generally obtained via [GarbageCollectionNotificationInfo#getGcAction()](https://docs.oracle.com/en/java/javase/11/docs/api/jdk.management/com/sun/management/GarbageCollectionNotificationInfo.html#getGcAction()).
"""


JVM_GC_NAME = "jvm.gc.name"
"""
Name of the garbage collector.
Note: Garbage collector name is generally obtained via [GarbageCollectionNotificationInfo#getGcName()](https://docs.oracle.com/en/java/javase/11/docs/api/jdk.management/com/sun/management/GarbageCollectionNotificationInfo.html#getGcName()).
"""


JVM_MEMORY_POOL_NAME = "jvm.memory.pool.name"
"""
Name of the memory pool.
Note: Pool names are generally obtained via [MemoryPoolMXBean#getName()](https://docs.oracle.com/en/java/javase/11/docs/api/java.management/java/lang/management/MemoryPoolMXBean.html#getName()).
"""


JVM_MEMORY_TYPE = "jvm.memory.type"
"""
The type of memory.
"""


JVM_THREAD_DAEMON = "jvm.thread.daemon"
"""
Whether the thread is daemon or not.
"""


JVM_THREAD_STATE = "jvm.thread.state"
"""
State of the thread.
"""

class JvmMemoryTypeValues(Enum):
    HEAP = "heap"
    """Heap memory."""

    NON_HEAP = "non_heap"
    """Non-heap memory."""
class JvmThreadStateValues(Enum):
    NEW = "new"
    """A thread that has not yet started is in this state."""

    RUNNABLE = "runnable"
    """A thread executing in the Java virtual machine is in this state."""

    BLOCKED = "blocked"
    """A thread that is blocked waiting for a monitor lock is in this state."""

    WAITING = "waiting"
    """A thread that is waiting indefinitely for another thread to perform a particular action is in this state."""

    TIMED_WAITING = "timed_waiting"
    """A thread that is waiting for another thread to perform an action for up to a specified waiting time is in this state."""

    TERMINATED = "terminated"
    """A thread that has exited is in this state."""
