# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import abc
import random

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
    """

    def generate_span_id(self) -> int:
        span_id = random.getrandbits(64)
        while span_id == trace.INVALID_SPAN_ID:
            span_id = random.getrandbits(64)
        return span_id

    def generate_trace_id(self) -> int:
        trace_id = random.getrandbits(128)
        while trace_id == trace.INVALID_TRACE_ID:
            trace_id = random.getrandbits(128)
        return trace_id
