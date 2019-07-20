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


class Resource:
    def __init__(self, labels: Dict[str, str]):
        """
        Construct a resource. Direct calling of the
        constructor is discouraged, as it cannot
        take advantage of caching and restricts
        to the type of object that can be returned.
        """
        self._labels = labels

    @staticmethod
    def create(labels: Dict[str, str]) -> "Resource":
        """
        create a new resource. This is the recommended
        method to use to create a new resource.
        """
        return Resource(labels)

    def merge(self, other: Union["Resource", None]) -> "Resource":
        """
        Perform a merge of the resources, resulting
        in a union of the resource objects.

        labels that exist in the main Resource take
        precedence unless the label value is empty.
        """
        if other is None:
            return self
        if not self._labels:
            return other
        merged_labels = self.get_labels().copy()
        for key, value in other.get_labels().items():
            if key not in merged_labels or merged_labels[key] == "":
                merged_labels[key] = value
        return Resource(merged_labels)

    def get_labels(self) -> Dict[str, str]:
        """
        Return the labels associated with this resource.

        get_labels exposes the raw internal dictionary,
        and as such it is not recommended to copy the
        result if it is desired to mutate the result.
        """
        return self._labels

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Resource):
            return False
        return self.get_labels() == other.get_labels()
