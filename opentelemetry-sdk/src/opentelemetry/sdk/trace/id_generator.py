# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Generation of the trace and span identifiers the SDK puts on new spans.

``TracerProvider`` holds one ``IdGenerator`` and asks it for a trace id
whenever a root span is created, and for a span id on every span. Replacing
the generator is the way to make the SDK produce ids that an external system
has already chosen, for example ids carried in from another tracing
implementation.
"""

import abc
import random

from opentelemetry import trace


class IdGenerator(abc.ABC):
    """Source of the trace ids and span ids used for new spans.

    Subclasses must implement both abstract methods. Neither of them may
    return the invalid all-zero id. Nothing in the SDK enforces that: a span
    whose context reports itself invalid is still handed to the processors
    and exported with those ids, and it is the backend that is left to reject
    it.
    """

    @abc.abstractmethod
    def generate_span_id(self) -> int:
        """Get a new span ID.

        Returns:
            A 64-bit int for use as a span ID
        """

    @abc.abstractmethod
    def generate_trace_id(self) -> int:
        """Get a new trace ID.

        Implementations should at least make the 56 least significant bits
        uniformly random. Samplers like the `TraceIdRatioBased` sampler rely on
        this randomness to make sampling decisions.

        If the implementation does randomly generate the 56 least significant bits,
        it should also implement `is_trace_id_random` to return True.

        See `the specification on TraceIdRatioBased <https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/trace/sdk.md#traceidratiobased>`_.

        Returns:
            A 128-bit int for use as a trace ID
        """

    # pylint: disable=no-self-use
    def is_trace_id_random(self) -> bool:
        """Indicates whether generated trace IDs are random.

        When True, the `trace-id` field will have the `random-trace-id` flag set
        in the W3C traceparent header. Per the W3C Trace Context specification,
        this indicates that at least the 7 rightmost bytes (56 bits) of the
        trace ID were generated randomly with uniform distribution.

        See `the W3C Trace Context specification <https://www.w3.org/TR/trace-context-2/#considerations-for-trace-id-field-generation>`_.

        Returns:
            True if this generator produces random IDs, False otherwise.
        """
        # By default, return False for backwards compatibility.
        return False


class RandomIdGenerator(IdGenerator):
    """The default ID generator for TracerProvider which randomly generates all
    bits when generating IDs.
    """

    def generate_span_id(self) -> int:
        """Draw 64 random bits for a span id.

        The draw is repeated while it yields the invalid all-zero span id, so
        the returned value is always a valid span id. ``random`` is seeded by
        the interpreter and is not cryptographically strong, so the ids are
        unsuitable as secrets.

        Returns:
            A 64-bit int for use as a span ID.
        """
        span_id = random.getrandbits(64)
        while span_id == trace.INVALID_SPAN_ID:
            span_id = random.getrandbits(64)
        return span_id

    def generate_trace_id(self) -> int:
        """Draw 128 random bits for a trace id.

        Every bit is random, not only the 56 least significant ones the
        specification requires, which is why ``is_trace_id_random`` reports
        ``True``. The draw is repeated while it yields the invalid all-zero
        trace id.

        Returns:
            A 128-bit int for use as a trace ID.
        """
        trace_id = random.getrandbits(128)
        while trace_id == trace.INVALID_TRACE_ID:
            trace_id = random.getrandbits(128)
        return trace_id

    def is_trace_id_random(self) -> bool:
        """Report that the trace ids of this generator are random.

        Returns:
            ``True`` always, which makes the SDK set the random trace id flag
            on the trace flags of spans whose trace id came from here.
        """
        return True
