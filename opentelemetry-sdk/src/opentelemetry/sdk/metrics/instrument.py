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

from opentelemetry.metrics.instrument import (
    Counter,
    ObservableCounter,
    UpDownCounter,
    ObservableUpDownCounter,
    Histogram,
    ObservableGauge
)

from opentelemetry.sdk.metrics.aggregation import (
    SumAggregation,
    LastValueAggregation,
    ExplicitBucketHistogramAggregation,
)


class Counter(Counter):

    def __init__(
        self,
        aggregation=SumAggregation,
        aggregation_config={}
    ):
        self._aggregation = aggregation(**aggregation_config)
        super().__init__()

    def add(self, amount, attributes=None):
        pass


class UpDownCounter(UpDownCounter):

    def __init__(
        self,
        aggregation=SumAggregation,
        aggregation_config={}
    ):
        self._aggregation = aggregation(**aggregation_config)
        super().__init__()

    def add(self, amount, attributes=None):
        pass


class ObservableCounter(ObservableCounter):

    def __init__(
        self,
        aggregation=SumAggregation,
        aggregation_config={}
    ):
        self._aggregation = aggregation(**aggregation_config)
        super().__init__()


class ObservableUpDownCounter(ObservableUpDownCounter):

    def __init__(
        self,
        aggregation=SumAggregation,
        aggregation_config={}
    ):
        self._aggregation = aggregation(**aggregation_config)
        super().__init__()


class Histogram(Histogram):

    def __init__(
        self,
        aggregation=ExplicitBucketHistogramAggregation,
        aggregation_config={}
    ):
        self._aggregation = aggregation(**aggregation_config)
        super().__init__()

    def add(self, amount, attributes=None):
        pass


class ObservableGauge(ObservableGauge):

    def __init__(
        self,
        aggregation=LastValueAggregation,
        aggregation_config={}
    ):
        self._aggregation = aggregation(**aggregation_config)
        super().__init__()
