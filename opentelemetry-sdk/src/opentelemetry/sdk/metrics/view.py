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

import logging
import threading
from collections import defaultdict
from typing import Sequence, Tuple, Type

from opentelemetry.metrics import (
    Counter,
    InstrumentT,
    SumObserver,
    UpDownCounter,
    UpDownSumObserver,
    ValueObserver,
    ValueRecorder,
    ValueT,
)
from opentelemetry.sdk.metrics.export.aggregate import (
    Aggregator,
    LastValueAggregator,
    MinMaxSumCountAggregator,
    SumAggregator,
    ValueObserverAggregator,
)

logger = logging.getLogger(__name__)


class ViewData:
    def __init__(self, labels: Tuple[Tuple[str, str]], aggregator: Aggregator):
        self.labels = labels
        self.aggregator = aggregator

    def record(self, value: ValueT):
        self.aggregator.update(value)

    # Uniqueness is based on labels and aggregator type
    def __hash__(self):
        return hash((self.labels, self.aggregator.__class__))

    def __eq__(self, other):
        return (
            self.labels == other.labels
            and self.aggregator.__class__ == other.aggregator.__class__
        )


class ViewConfig:

    UNGROUPED = 0
    LABEL_KEYS = 1
    DROP_ALL = 2


class View:
    def __init__(
        self,
        metric: InstrumentT,
        aggregator: Aggregator,
        label_keys: Sequence[str] = None,
        config: ViewConfig = ViewConfig.UNGROUPED,
    ):
        self.metric = metric
        self.aggregator = aggregator
        if label_keys is None:
            label_keys = []
        self.label_keys = sorted(label_keys)
        self.config = config

    # Uniqueness is based on metric, aggregator type, ordered label keys and ViewConfig
    def __hash__(self):
        return hash(
            (self.metric, self.aggregator, tuple(self.label_keys), self.config)
        )

    def __eq__(self, other):
        return (
            self.metric == other.metric
            and self.aggregator.__class__ == other.aggregator.__class__
            and self.label_keys == other.label_keys
            and self.config == other.config
        )


class ViewManager:
    def __init__(self):
        self.views = defaultdict(set)  #  Map[Metric, Set]
        self._view_lock = threading.Lock()

    def register_view(self, view):
        with self._view_lock:
            if view not in self.views[view.metric]:
                self.views[view.metric].add(view)
            else:
                logger.warning("View already registered.")
                return

    def unregister_view(self, view):
        with self._view_lock:
            if self.views.get(view.metric) is None:
                logger.warning("Metric for view does not exist.")
            elif view in self.views.get(view.metric):
                self.views.get(view.metric).remove(view)

    def generate_view_datas(self, metric, labels):
        view_datas = set()
        views = self.views.get(metric)
        # No views configured, use default aggregations
        if views is None:
            aggregator = get_default_aggregator(metric)
            # Default config aggregates on all label keys
            view_datas.add(ViewData(tuple(labels), aggregator))
        else:
            for view in views:
                updated_labels = []
                if view.config == ViewConfig.LABEL_KEYS:
                    label_key_set = set(view.label_keys)
                    for label in labels:
                        # Only keep labels that are in configured label_keys
                        if label[0] in label_key_set:
                            updated_labels.append(label)
                    updated_labels = tuple(updated_labels)
                elif view.config == ViewConfig.UNGROUPED:
                    updated_labels = labels
                # ViewData that is duplicate (same labels and aggregator) will be
                # aggregated together as one
                view_datas.add(
                    ViewData(tuple(updated_labels), view.aggregator)
                )
        return view_datas


def get_default_aggregator(instrument: InstrumentT) -> Aggregator:
    """Returns an aggregator based on metric instrument's type.

    Aggregators keep track of and updates values when metrics get updated.
    """
    # pylint:disable=R0201
    instrument_type = instrument.__class__
    if issubclass(instrument_type, (Counter, UpDownCounter)):
        return SumAggregator()
    if issubclass(instrument_type, (SumObserver, UpDownSumObserver)):
        return LastValueAggregator()
    if issubclass(instrument_type, ValueRecorder):
        return MinMaxSumCountAggregator()
    if issubclass(instrument_type, ValueObserver):
        return ValueObserverAggregator()
    logger.warning("No default aggregator configured for: %s", instrument_type)
    return SumAggregator()
