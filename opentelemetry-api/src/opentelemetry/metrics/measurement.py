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

# pylint: disable=too-many-ancestors
# type:ignore


from abc import ABC, abstractmethod


class Measurement(ABC):
    @property
    def value(self):
        return self._value

    @property
    def attributes(self):
        return self._attributes

    @abstractmethod
    def __init__(self, value, attributes=None):
        self._value = value
        self._attributes = attributes


class DefaultMeasurement(Measurement):
    def __init__(self, value, attributes=None):
        super().__init__(value, attributes=attributes)
