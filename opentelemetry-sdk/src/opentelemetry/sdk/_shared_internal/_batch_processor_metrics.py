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

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol


class BatchProcessorMetrics(Protocol):
    def drop_items(self, count: int) -> None: ...

    def finish_items(self, count: int, error: Exception | None) -> None: ...


class BatchProcessorMetricsFactory(Protocol):
    def __call__(
        self, *, get_queue_size: Callable[[], int]
    ) -> BatchProcessorMetrics: ...
