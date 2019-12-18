# Copyright 2019, OpenTelemetry Authors
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

import abc

class Aggregator(abc.ABC):
    """Base class for aggregators.

    Aggregators are responsible for holding aggregated values and taking a
    snapshot of these values upon export (check_point).
    """

    def __init__(self):
        self.current = None
        self.check_point = None

    @abc.abstractmethod
    def update(self, value):
        pass

    @abc.abstractmethod
    def checkpoint(self):
        pass

class CounterAggregator(Aggregator):
    """Aggregator for `Counter` metrics."""

    def __init__(self):
        super().__init__()
        self.current = 0
        self.check_point = 0

    def update(self, value):
        self.current += value

    def checkpoint(self):
        # TODO: Implement lock-free algorithm for concurrency
        self.check_point = self.current
