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


from typing import (
    Callable,
    Final,
    Generator,
    Iterable,
    Optional,
    Sequence,
    Union,
)

from opentelemetry.metrics import (
    CallbackOptions,
    Counter,
    Meter,
    ObservableGauge,
    Observation,
)

# pylint: disable=invalid-name
CallbackT = Union[
    Callable[[CallbackOptions], Iterable[Observation]],
    Generator[Iterable[Observation], CallbackOptions, None],
]

K8S_NODE_CPU_TIME: Final = "k8s.node.cpu.time"
"""
Total CPU time consumed
Instrument: counter
Unit: s
Note: Total CPU time consumed by the specific Node on all available CPU cores.
"""


def create_k8s_node_cpu_time(meter: Meter) -> Counter:
    """Total CPU time consumed"""
    return meter.create_counter(
        name=K8S_NODE_CPU_TIME,
        description="Total CPU time consumed",
        unit="s",
    )


K8S_NODE_CPU_USAGE: Final = "k8s.node.cpu.usage"
"""
Node's CPU usage, measured in cpus. Range from 0 to the number of allocatable CPUs
Instrument: gauge
Unit: {cpu}
Note: CPU usage of the specific Node on all available CPU cores, averaged over the sample window.
"""


def create_k8s_node_cpu_usage(
    meter: Meter, callbacks: Optional[Sequence[CallbackT]]
) -> ObservableGauge:
    """Node's CPU usage, measured in cpus. Range from 0 to the number of allocatable CPUs"""
    return meter.create_observable_gauge(
        name=K8S_NODE_CPU_USAGE,
        callbacks=callbacks,
        description="Node's CPU usage, measured in cpus. Range from 0 to the number of allocatable CPUs",
        unit="{cpu}",
    )


K8S_NODE_MEMORY_USAGE: Final = "k8s.node.memory.usage"
"""
Memory usage of the Node
Instrument: gauge
Unit: By
Note: Total memory usage of the Node.
"""


def create_k8s_node_memory_usage(
    meter: Meter, callbacks: Optional[Sequence[CallbackT]]
) -> ObservableGauge:
    """Memory usage of the Node"""
    return meter.create_observable_gauge(
        name=K8S_NODE_MEMORY_USAGE,
        callbacks=callbacks,
        description="Memory usage of the Node",
        unit="By",
    )


K8S_POD_CPU_TIME: Final = "k8s.pod.cpu.time"
"""
Total CPU time consumed
Instrument: counter
Unit: s
Note: Total CPU time consumed by the specific Pod on all available CPU cores.
"""


def create_k8s_pod_cpu_time(meter: Meter) -> Counter:
    """Total CPU time consumed"""
    return meter.create_counter(
        name=K8S_POD_CPU_TIME,
        description="Total CPU time consumed",
        unit="s",
    )


K8S_POD_CPU_USAGE: Final = "k8s.pod.cpu.usage"
"""
Pod's CPU usage, measured in cpus. Range from 0 to the number of allocatable CPUs
Instrument: gauge
Unit: {cpu}
Note: CPU usage of the specific Pod on all available CPU cores, averaged over the sample window.
"""


def create_k8s_pod_cpu_usage(
    meter: Meter, callbacks: Optional[Sequence[CallbackT]]
) -> ObservableGauge:
    """Pod's CPU usage, measured in cpus. Range from 0 to the number of allocatable CPUs"""
    return meter.create_observable_gauge(
        name=K8S_POD_CPU_USAGE,
        callbacks=callbacks,
        description="Pod's CPU usage, measured in cpus. Range from 0 to the number of allocatable CPUs",
        unit="{cpu}",
    )


K8S_POD_MEMORY_USAGE: Final = "k8s.pod.memory.usage"
"""
Memory usage of the Pod
Instrument: gauge
Unit: By
Note: Total memory usage of the Pod.
"""


def create_k8s_pod_memory_usage(
    meter: Meter, callbacks: Optional[Sequence[CallbackT]]
) -> ObservableGauge:
    """Memory usage of the Pod"""
    return meter.create_observable_gauge(
        name=K8S_POD_MEMORY_USAGE,
        callbacks=callbacks,
        description="Memory usage of the Pod",
        unit="By",
    )
