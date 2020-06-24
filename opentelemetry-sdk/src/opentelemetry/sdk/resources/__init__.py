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

import os
import typing
from json import dumps

from opentelemetry.context import attach, detach, set_value

LabelValue = typing.Union[str, bool, int, float]
Labels = typing.Dict[str, LabelValue]


class Resource:
    def __init__(self, labels: Labels):
        self._labels = labels.copy()

    @staticmethod
    def create(labels: Labels) -> "Resource":
        if not labels:
            return _EMPTY_RESOURCE
        return Resource(labels)

    @staticmethod
    def create_empty() -> "Resource":
        return _EMPTY_RESOURCE

    @property
    def labels(self) -> Labels:
        return self._labels.copy()

    def merge(self, other: "Resource") -> "Resource":
        merged_labels = self.labels
        # pylint: disable=protected-access
        for key, value in other._labels.items():
            if key not in merged_labels or merged_labels[key] == "":
                merged_labels[key] = value
        return Resource(merged_labels)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Resource):
            return False
        return self._labels == other._labels

    def __hash__(self):
        return hash(dumps(self._labels, sort_keys=True))


_EMPTY_RESOURCE = Resource({})


class ResourceDetector:
    def __init__(self, crash_on_error=False):
        self.crash_on_error = crash_on_error

    # pylint: disable=no-self-use
    def detect(self) -> "Resource":
        return _EMPTY_RESOURCE


class OTELResourceDetector:
    # pylint: disable=no-self-use
    def detect(self) -> "Resource":
        env_resources_items = os.environ["OTEL_RESOURCE"]
        env_resource_map = {}
        if env_resources_items:
            for item in env_resources_items.split(","):
                key, value = item.split("=")
                env_resource_map[key] = value
        return Resource(env_resource_map)


def get_aggregated_resources(
    detectors: typing.List["ResourceDetector"],
    initial_resource=None,
    detect_from_env=True,
) -> "Resource":
    final_resource = initial_resource or _EMPTY_RESOURCE
    if detect_from_env:
        final_resource = final_resource.merge(OTELResourceDetector().detect())
    token = attach(set_value("suppress_instrumentation", True))
    for detector in detectors:
        try:
            detected_resources = detector.detect()
        # pylint: disable=broad-except
        except Exception as ex:
            if detector.crash_on_error:
                raise ex
            detected_resources = _EMPTY_RESOURCE
        finally:
            final_resource = final_resource.merge(detected_resources)
    detach(token)
    return final_resource
