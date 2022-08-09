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

from abc import ABC, abstractmethod


# FIXME Make sure this is a good name, find a better one if necessary.
class ExponentialHistogramMapping(ABC):
    def __init__(self, scale: int):
        self._scale = scale

    @abstractmethod
    def map_to_index(self, value: float) -> int:
        """
        MapToIndex maps positive floating point values to indexes
        corresponding to Scale().  Implementations are not expected
        to handle zeros, +Inf, NaN, or negative values.
        """

    # FIXME Should this be a property?
    @abstractmethod
    def get_lower_boundary(self, index: int) -> float:
        """
        LowerBoundary returns the lower boundary of a given bucket
        index.  The index is expected to map onto a range that is
        at least partially inside the range of normalized floating
        point values.  If the corresponding bucket's upper boundary
        is less than or equal to 0x1p-1022, UnderflowError will be
        raised. If the corresponding bucket's lower boundary is
        greater than math.MaxFloat64, OverflowError will be raised.
        """

    @property
    @abstractmethod
    def scale(self) -> int:
        """
        Scale returns the parameter that controls the resolution of
        this mapping.  For details see:
        https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/datamodel.md#exponential-scale
        """


# FIXME make sure this is a good name
class ExponentialMappingUnderflowError(Exception):
    """
    Raised when computing the lower boundary of an index that maps into a
    denormalized floating point value.
    """


# FIXME make sure this is a good name
class ExponentialMappingOverflowError(Exception):
    """
    Raised when computing the lower boundary of an index that maps into +Inf.
    """
