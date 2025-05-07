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

import abc
import random
from random import Random
from typing import Optional

from opentelemetry import trace


class IdGenerator(abc.ABC):
    @abc.abstractmethod
    def generate_span_id(self) -> int:
        """Get a new span ID.

        Returns:
            A 64-bit int for use as a span ID
        """

    @abc.abstractmethod
    def generate_trace_id(self) -> int:
        """Get a new trace ID.

        Implementations should at least make the 64 least significant bits
        uniformly random. Samplers like the `TraceIdRatioBased` sampler rely on
        this randomness to make sampling decisions.

        See `the specification on TraceIdRatioBased <https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/trace/sdk.md#traceidratiobased>`_.

        Returns:
            A 128-bit int for use as a trace ID
        """


class RandomIdGenerator(IdGenerator):
    """The default ID generator for TracerProvider which randomly generates all
    bits when generating IDs.

    Args:
        rng: A random number generator. Defaults to the global random instance.
            It is recommended to use a fresh `Random()` instead of the default
            to avoid potential conflicts with the global random instance
            (duplicate ids across multiple processes when a constant global
            random seed is set).
    """

    def __init__(self, rng: Optional[Random] = None) -> None:
        if rng is None:
            rng = random  # Just a hack to preserve backward compatibility, otherwise it does not quite match the type hint.
        self._rng = rng

    def generate_span_id(self) -> int:
        span_id = self._rng.getrandbits(64)
        while span_id == trace.INVALID_SPAN_ID:
            span_id = self._rng.getrandbits(64)
        return span_id

    def generate_trace_id(self) -> int:
        trace_id = self._rng.getrandbits(128)
        while trace_id == trace.INVALID_TRACE_ID:
            trace_id = self._rng.getrandbits(128)
        return trace_id
