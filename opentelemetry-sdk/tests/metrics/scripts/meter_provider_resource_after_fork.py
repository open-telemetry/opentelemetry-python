# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import json
import os

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import PROCESS_PID


def _resource_pids(metrics_data) -> list[int]:
    return [
        resource_metric.resource.attributes[PROCESS_PID]
        for resource_metric in metrics_data.resource_metrics
    ]


def _metric_names(metrics_data) -> list[str]:
    return sorted(
        metric.name
        for resource_metric in metrics_data.resource_metrics
        for scope_metric in resource_metric.scope_metrics
        for metric in scope_metric.metrics
    )


# pylint: disable-next=too-many-locals
def main() -> None:
    reader = InMemoryMetricReader()
    meter_provider = MeterProvider(
        metric_readers=[reader], shutdown_on_exit=False
    )
    meter = meter_provider.get_meter("cached")
    counter = meter.create_counter("cached_counter")
    parent_pid = os.getpid()
    # pylint: disable-next=protected-access
    parent_resource_pid = meter_provider._sdk_config.resource.attributes[
        PROCESS_PID
    ]

    pid = os.fork()
    if not pid:
        child_pid = os.getpid()
        new_meter = meter_provider.get_meter("new")
        new_counter = new_meter.create_counter("new_counter")
        counter.add(1)
        new_counter.add(1)
        metrics_data = reader.get_metrics_data()
        print(
            json.dumps(
                {
                    "child_pid": child_pid,
                    # pylint: disable-next=protected-access
                    "provider_pid": meter_provider._sdk_config.resource.attributes[
                        PROCESS_PID
                    ],
                    "exported_resource_pids": _resource_pids(metrics_data),
                    "metric_names": _metric_names(metrics_data),
                }
            ),
            flush=True,
        )
        # pylint: disable-next=protected-access
        os._exit(0)

    os.waitpid(pid, 0)
    print(
        json.dumps(
            {
                "parent_pid": parent_pid,
                "parent_resource_pid": parent_resource_pid,
                # pylint: disable-next=protected-access
                "parent_resource_pid_after_fork": meter_provider._sdk_config.resource.attributes[
                    PROCESS_PID
                ],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
