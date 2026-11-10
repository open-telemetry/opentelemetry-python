# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from enum import Enum
from typing import Final

CPU_LOGICAL_NUMBER: Final = "cpu.logical_number"
"""
The identifier of a logical execution target (CPU) as seen by the operating system, in the range [0..n-1].
Note: On systems with simultaneous multithreading (SMT) enabled — such as Intel Hyper-Threading or AMD SMT — this value will usually differ from the physical core number, because each core presents multiple logical CPUs for the system to use.
"""

CPU_MODE: Final = "cpu.mode"
"""
The mode of the CPU.
"""


class CpuModeValues(Enum):
    USER = "user"
    """User."""
    SYSTEM = "system"
    """System."""
    NICE = "nice"
    """Nice."""
    IDLE = "idle"
    """Idle."""
    IOWAIT = "iowait"
    """IO Wait."""
    INTERRUPT = "interrupt"
    """Interrupt."""
    STEAL = "steal"
    """Steal."""
    KERNEL = "kernel"
    """Deprecated: Replaced by `system`."""
