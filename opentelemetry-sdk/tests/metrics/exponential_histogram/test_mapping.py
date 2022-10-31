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

from math import inf
from unittest import TestCase

from opentelemetry.sdk.metrics._internal.exponential_histogram.mapping import (
    Mapping,
)


class TestMapping(TestCase):
    def test_lock(self):
        class Child0(Mapping):
            def _get_max_scale(self) -> int:
                return inf

            def _get_min_scale(self) -> int:
                return -inf

            def map_to_index(self, value: float) -> int:
                pass

            def get_lower_boundary(self, index: int) -> float:
                pass

        class Child1(Mapping):
            def _get_max_scale(self) -> int:
                return inf

            def _get_min_scale(self) -> int:
                return -inf

            def map_to_index(self, value: float) -> int:
                pass

            def get_lower_boundary(self, index: int) -> float:
                pass

        child_0 = Child0(0)
        child_1 = Child1(1)

        self.assertIsNot(child_0._mappings, child_1._mappings)
        self.assertIsNot(child_0._mappings_lock, child_1._mappings_lock)
