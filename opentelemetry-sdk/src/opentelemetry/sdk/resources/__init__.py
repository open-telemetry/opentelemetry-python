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
from typing import Any, Dict, Union
from opentelemetry.resources import Resource


class DefaultResource(Resource):
    def __init__(self, labels):
        self._labels = labels

    @property
    def labels(self):
        return self._labels

    @staticmethod
    def create(labels):
        return DefaultResource(labels)

    def merge(self, other):
        if other is None:
            return self
        if not self._labels:
            return other
        merged_labels = self.labels.copy()
        for key, value in other.labels.items():
            if key not in merged_labels or merged_labels[key] == "":
                merged_labels[key] = value
        return DefaultResource(merged_labels)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DefaultResource):
            return False
        return self.labels == other.labels
