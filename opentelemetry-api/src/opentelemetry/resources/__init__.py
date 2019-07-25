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
from abc import ABC, abstractmethod
from typing import Dict, Union


class Resource(ABC):
    """This the interface that resources must implement"""
    def __init__(self, labels: Dict[str, str]):
        """Construct a resource.

        Direct calling of the constructor is discouraged, as it cannot
        take advantage of caching and restricts to the type of object
        that can be returned.
        """
        self._labels = labels

    @staticmethod
    def create(labels: Dict[str, str]) -> "Resource":
        """create a new resource.

        Args:
            labels: the labels that define the resource

        Returns:
            The resource with the labels in question
        """
    @property
    @abstractmethod
    def labels(self) -> Dict[str, str]:
        """Return the label dictionary associated with this resource.

        Returns:
            A dictionary with the labels of the resource
        """
    def merge(self, other: Union["Resource", None]) -> "Resource":
        """Return a resource with the union of labels for both resources.

        Labels that exist in the main Resource take
        precedence unless the label value is the empty string.

        Args:
            other: the resource to merge in
        """
