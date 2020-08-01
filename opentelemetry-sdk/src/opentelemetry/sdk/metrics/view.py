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
from typing import Optional, Sequence, Tuple

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
        aggregator: type,
        aggregator_config: Optional[dict] = None,
        label_keys: Optional[Sequence[str]] = None,
        view_config: ViewConfig = ViewConfig.UNGROUPED,
    ):
        self.metric = metric
        self.aggregator = aggregator
        if aggregator_config is None:
            aggregator_config = {}
        self.aggregator_config = aggregator_config
        if label_keys is None:
            label_keys = []
        self.label_keys = sorted(label_keys)
        self.view_config = view_config
        self.view_datas = set()

    def get_view_data(self, labels):
        """Find an existing ViewData for this set of labels. If that ViewData
            does not exist, create a new one to represent the labels
        """
        active_labels = []
        if self.view_config == ViewConfig.LABEL_KEYS:
            # reduce the set of labels to only labels specified in label_keys
            active_labels = {
                (lk, lv) for lk, lv in labels if lk in set(self.label_keys)
            }
            active_labels = tuple(active_labels)
        elif self.view_config == ViewConfig.UNGROUPED:
            active_labels = labels

        for view_data in self.view_datas:
            if view_data.labels == active_labels:
                return view_data
        new_view_data = ViewData(
            active_labels, self.aggregator(self.aggregator_config)
        )
        self.view_datas.add(new_view_data)
        return new_view_data

    # Uniqueness is based on metric, aggregator type, aggregator config,
    # ordered label keys and ViewConfig
    def __hash__(self):
        return hash(
            (
                self.metric,
                self.aggregator.__class__,
                tuple(self.label_keys),
                tuple(self.aggregator_config),
                self.view_config,
            )
        )

    def __eq__(self, other):
        return (
            self.metric == other.metric
            and self.aggregator.__class__ == other.aggregator.__class__
            and self.label_keys == other.label_keys
            and self.aggregator_config == other.aggregator_config
            and self.view_config == other.view_config
        )


class ViewManager:
    def __init__(self):
        self.views = defaultdict(set)  # Map[Metric, Set]
        self._view_lock = threading.Lock()
        self.view_datas = set()

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

    def get_view_datas(self, metric, labels):
        view_datas = set()
        views = self.views.get(metric)
        # No views configured, use default aggregations
        if views is None:
            # make a default view for the metric
            default_view = View(metric, get_default_aggregator(metric))
            self.register_view(default_view)
            views = [default_view]

        for view in views:
            view_datas.add(view.get_view_data(labels))

        return view_datas


def get_default_aggregator(instrument: InstrumentT) -> Aggregator:
    """Returns an aggregator based on metric instrument's type.

    Aggregators keep track of and updates values when metrics get updated.
    """
    # pylint:disable=R0201
    instrument_type = instrument.__class__
    if issubclass(instrument_type, (Counter, UpDownCounter)):
        return SumAggregator
    if issubclass(instrument_type, (SumObserver, UpDownSumObserver)):
        return LastValueAggregator
    if issubclass(instrument_type, ValueRecorder):
        return MinMaxSumCountAggregator
    if issubclass(instrument_type, ValueObserver):
        return ValueObserverAggregator
    logger.warning("No default aggregator configured for: %s", instrument_type)
    return SumAggregator
