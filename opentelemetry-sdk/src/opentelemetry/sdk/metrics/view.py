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

from opentelemetry.sdk.metrics.export.aggregate import (
    CountAggregation,
    SummaryAggregation
)

logger = logging.getLogger(__name__)


class ViewData:

    def __init__(self, view):
        self.view = view
        self.aggregators = {} # Label to aggregator

    def record(self, value, labels):
        # Aggregate based on ViewConfig
        if self.view.config == ViewConfig.LABEL_KEYS:
            updated_labels = []
            label_key_set = set(self.view.label_keys)
            for label in labels:
                if label[0] in label_key_set:
                    updated_labels.append(label)
            labels = tuple(updated_labels)
        elif self.view.config == ViewConfig.DROP_ALL:
            labels = ()
        if self.aggregators.get(labels) is None:
            self.aggregators[labels] = self.view.new_aggregator()
        # Labels are already converted to tuples to be used as keys
        self.aggregators[labels].update(value)


class ViewConfig:

    UNGROUPED = 0
    LABEL_KEYS = 1
    DROP_ALL = 2


class View:

    def __init__(self, metric, aggregation, label_keys=None, config=ViewConfig.UNGROUPED):
        self.metric = metric
        self.aggregation = aggregation
        if label_keys is None:
            label_keys = []
        self.label_keys = sorted(label_keys)
        self.config = config

    def new_aggregator(self):
        return self.aggregation.new_aggregator()

    # Uniqueness is based on metric, aggregation type, ordered label keys and ViewConfig
    def __hash__(self):
        return hash(
            (self.metric,
            self.aggregation.__class__,
            tuple(self.label_keys),
            self.config)
        )

    def __eq__(self, other):
        return self.metric == other.metric and \
            self.aggregation.__class__ == other.aggregation.__class__ and \
            self.label_keys.sort() == other.label_keys.sort() and \
            self.config == other.config


class ViewManager:

    def __init__(self):
        self.views = {} # metric to set of views
        self.view_datas = {} # metric to set of view datas
        self._view_lock = threading.Lock()

    def register_view(self, view):
        with self._view_lock:
            if self.views.get(view.metric) is None:
                self.views[view.metric] = {view}
                self.view_datas[view.metric] = {ViewData(view)}
            elif view not in self.views.get(view.metric):
                self.views[view.metric].add(view)
                self.view_datas[view.metric].add(ViewData(view))
            else:
                logger.warning("View already registered.")
                return

    def unregister_view(self, view):
        with self._view_lock:
            if self.views.get(view.metric) is None:
                logger.warning("Metric for view does not exist.")
            elif view in self.views.get(view.metric):
                self.views.get(view.metric).remove(view)

    def record(self, metric, labels, value):
        view_datas = self.view_datas.get(metric)
        # If no views registered for metric, use default aggregation
        if view_datas is None:
            aggregation = CountAggregation() \
                if metric.__class__.__name__ == "Counter" else SummaryAggregation()
            view = View(metric, aggregation)
            self.register_view(view)
        with self._view_lock:
            view_datas = self.view_datas.get(metric, {})
            for view_data in view_datas:
                # Record the value with the given labels to the view data
                view_data.record(value, labels)
