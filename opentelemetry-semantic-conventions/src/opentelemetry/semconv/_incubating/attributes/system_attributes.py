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

from deprecated import deprecated

SYSTEM_CPU_LOGICAL_NUMBER: Final = "system.cpu.logical_number"
"""
The logical CPU number [0..n-1].
"""

SYSTEM_CPU_STATE: Final = "system.cpu.state"
"""
The state of the CPU.
"""

SYSTEM_DEVICE: Final = "system.device"
"""
The device identifier.
"""

SYSTEM_FILESYSTEM_MODE: Final = "system.filesystem.mode"
"""
The filesystem mode.
"""

SYSTEM_FILESYSTEM_MOUNTPOINT: Final = "system.filesystem.mountpoint"
"""
The filesystem mount path.
"""

SYSTEM_FILESYSTEM_STATE: Final = "system.filesystem.state"
"""
The filesystem state.
"""

SYSTEM_FILESYSTEM_TYPE: Final = "system.filesystem.type"
"""
The filesystem type.
"""

SYSTEM_MEMORY_STATE: Final = "system.memory.state"
"""
The memory state.
"""

SYSTEM_NETWORK_STATE: Final = "system.network.state"
"""
A stateless protocol MUST NOT set this attribute.
"""

SYSTEM_PAGING_DIRECTION: Final = "system.paging.direction"
"""
The paging access direction.
"""

SYSTEM_PAGING_STATE: Final = "system.paging.state"
"""
The memory paging state.
"""

SYSTEM_PAGING_TYPE: Final = "system.paging.type"
"""
The memory paging type.
"""

SYSTEM_PROCESS_STATUS: Final = "system.process.status"
"""
The process state, e.g., [Linux Process State Codes](https://man7.org/linux/man-pages/man1/ps.1.html#PROCESS_STATE_CODES).
"""

SYSTEM_PROCESSES_STATUS: Final = "system.processes.status"
"""
Deprecated: Replaced by `system.process.status`.
"""


class SystemCpuStateValues(Enum):
    USER: Final = "user"
    """user."""
    SYSTEM: Final = "system"
    """system."""
    NICE: Final = "nice"
    """nice."""
    IDLE: Final = "idle"
    """idle."""
    IOWAIT: Final = "iowait"
    """iowait."""
    INTERRUPT: Final = "interrupt"
    """interrupt."""
    STEAL: Final = "steal"
    """steal."""


class SystemFilesystemStateValues(Enum):
    USED: Final = "used"
    """used."""
    FREE: Final = "free"
    """free."""
    RESERVED: Final = "reserved"
    """reserved."""


class SystemFilesystemTypeValues(Enum):
    FAT32: Final = "fat32"
    """fat32."""
    EXFAT: Final = "exfat"
    """exfat."""
    NTFS: Final = "ntfs"
    """ntfs."""
    REFS: Final = "refs"
    """refs."""
    HFSPLUS: Final = "hfsplus"
    """hfsplus."""
    EXT4: Final = "ext4"
    """ext4."""


class SystemMemoryStateValues(Enum):
    USED: Final = "used"
    """used."""
    FREE: Final = "free"
    """free."""
    SHARED: Final = "shared"
    """shared."""
    BUFFERS: Final = "buffers"
    """buffers."""
    CACHED: Final = "cached"
    """cached."""


class SystemNetworkStateValues(Enum):
    CLOSE: Final = "close"
    """close."""
    CLOSE_WAIT: Final = "close_wait"
    """close_wait."""
    CLOSING: Final = "closing"
    """closing."""
    DELETE: Final = "delete"
    """delete."""
    ESTABLISHED: Final = "established"
    """established."""
    FIN_WAIT_1: Final = "fin_wait_1"
    """fin_wait_1."""
    FIN_WAIT_2: Final = "fin_wait_2"
    """fin_wait_2."""
    LAST_ACK: Final = "last_ack"
    """last_ack."""
    LISTEN: Final = "listen"
    """listen."""
    SYN_RECV: Final = "syn_recv"
    """syn_recv."""
    SYN_SENT: Final = "syn_sent"
    """syn_sent."""
    TIME_WAIT: Final = "time_wait"
    """time_wait."""


class SystemPagingDirectionValues(Enum):
    IN: Final = "in"
    """in."""
    OUT: Final = "out"
    """out."""


class SystemPagingStateValues(Enum):
    USED: Final = "used"
    """used."""
    FREE: Final = "free"
    """free."""


class SystemPagingTypeValues(Enum):
    MAJOR: Final = "major"
    """major."""
    MINOR: Final = "minor"
    """minor."""


class SystemProcessStatusValues(Enum):
    RUNNING: Final = "running"
    """running."""
    SLEEPING: Final = "sleeping"
    """sleeping."""
    STOPPED: Final = "stopped"
    """stopped."""
    DEFUNCT: Final = "defunct"
    """defunct."""


@deprecated(reason="The attribute system.processes.status is deprecated - Replaced by `system.process.status`")  # type: ignore
class SystemProcessesStatusValues(Enum):
    RUNNING: Final = "running"
    """running."""
    SLEEPING: Final = "sleeping"
    """sleeping."""
    STOPPED: Final = "stopped"
    """stopped."""
    DEFUNCT: Final = "defunct"
    """defunct."""
