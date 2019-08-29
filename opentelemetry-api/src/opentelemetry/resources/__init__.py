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

import abc
import typing


class Resource(abc.ABC):
    """The interface that resources must implement."""

    @staticmethod
    @abc.abstractmethod
    def create(labels: typing.Dict[str, str]) -> "Resource":
        """Create a new resource.

        Args:
            labels: the labels that define the resource

        Returns:
            The resource with the labels in question

        """

    @property
    @abc.abstractmethod
    def labels(self) -> typing.Dict[str, str]:
        """Return the label dictionary associated with this resource.

        Returns:
            A dictionary with the labels of the resource

        """

    @abc.abstractmethod
    def merge(self, other: typing.Optional["Resource"]) -> "Resource":
        """Return a resource with the union of labels for both resources.

        Labels that exist in the main Resource take precedence unless the
        label value is the empty string.

        Args:
            other: The resource to merge in

        """
