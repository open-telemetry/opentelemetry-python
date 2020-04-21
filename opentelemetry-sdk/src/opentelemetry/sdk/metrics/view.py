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

logger = logging.getLogger(__name__)


class ViewData:

    def __init__(self, labels, aggregator_type):
        self.labels = labels
        self.aggregator = aggregator_type()


class View:

    def __init__(self, metric, aggregator_type, label_keys=None):
        self.metric = metric
        self.aggregator_type = aggregator_type
        self.view_datas = {} # Labels to ViewData
        self._view_datas_lock = threading.Lock()
        # TODO: add configuration for aggregators (histogram, etc.)
        # TODO: add label key configuration
        self.label_keys = label_keys
        if self.label_keys is None:
            self.label_keys = []

    def get_all_view_data(self):
        # We return a copy of the values because the dictionary can be can be
        # always changing
        return list(self.view_datas.values())

    def update_view_datas(self, labels, value):
        with self._view_datas_lock:
            view_data = self.view_datas.get(labels)
            if view_data is None:
                view_data = ViewData(labels, self.aggregator_type)
                self.view_datas[labels] = view_data
            view_data.aggregator.update(value)

    # Uniqueness of View is based on metric and aggregation type
    def __hash__(self):
        return hash((self.metric, self.aggregator_type))

    def __eq__(self, other):
        return self.metric == other.metric and \
            self.aggregator_type == other.aggregator_type


class ViewManager:

    def __init__(self):
        self.views = {} # metric to set of views
        self._view_lock = threading.Lock()

    def register_view(self, view):
        with self._view_lock:
            if self.views.get(view.metric) is None:
                self.views[view.metric] = {view}
            elif view not in self.views.get(view.metric):
                self.views[view.metric].add(view)
            else:
                logger.warning("View already registered.")

    def unregister_view(self, view):
        with self._view_lock:
            if self.views.get(view.metric) is None:
                logger.warning("Metric for view does not exist.")
            elif view in self.views.get(view.metric):
                self.views.get(view.metric).remove(view)

    def update_view(self, metric, labels, value):
        with self._view_lock:
            views = self.views.get(metric, {})
            # We only update if view was defined for the metric
            for view in views:
                # TODO: Check view configuration here to keep/drop keys
                # Find the view data corresponding to the labels
                view.update_view_datas(labels, value)
