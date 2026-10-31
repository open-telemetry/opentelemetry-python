# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The filters that decide which measurements may become exemplars.

A filter is consulted before a reservoir is, and answers from the
measurement alone without keeping any state. Three are provided here, and
``opentelemetry.sdk.metrics._internal.MeterProvider`` picks one from the
``OTEL_METRICS_EXEMPLAR_FILTER`` environment variable.
"""

from abc import ABC, abstractmethod

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.trace.span import INVALID_SPAN
from opentelemetry.util.types import Attributes


class ExemplarFilter(ABC):
    """``ExemplarFilter`` determines which measurements are eligible for becoming an
    ``Exemplar``.

    Exemplar filters are used to filter measurements before attempting to store them
    in a reservoir.

    Reference:
        https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md#exemplarfilter
    """

    @abstractmethod
    def should_sample(
        self,
        value: float,
        time_unix_nano: int,
        attributes: Attributes,
        context: Context,
    ) -> bool:
        """Returns whether or not a reservoir should attempt to filter a measurement.

        Args:
            value: The value of the measurement
            time_unix_nano: A timestamp that best represents when the
                measurement was taken
            attributes: The complete set of measurement attributes
            context: The Context of the measurement

        Returns:
            ``True`` when the measurement may be offered to a reservoir.
            An answer of ``True`` does not mean the measurement will be
            kept: the reservoir still decides that.

        Raises:
            NotImplementedError: Always, since this is the interface. A
                subclass overrides it.
        """
        raise NotImplementedError("ExemplarFilter.should_sample is not implemented")


class AlwaysOnExemplarFilter(ExemplarFilter):
    """An ExemplarFilter which makes all measurements eligible for being an Exemplar.

    Reference:
        https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md#alwayson
    """

    def should_sample(
        self,
        value: float,
        time_unix_nano: int,
        attributes: Attributes,
        context: Context,
    ) -> bool:
        """Returns whether or not a reservoir should attempt to filter a measurement.

        Args:
            value: The value of the measurement
            time_unix_nano: A timestamp that best represents when the
                measurement was taken
            attributes: The complete set of measurement attributes
            context: The Context of the measurement

        Returns:
            ``True``, whatever the arguments are. No argument is read.
        """
        return True


class AlwaysOffExemplarFilter(ExemplarFilter):
    """An ExemplarFilter which makes no measurements eligible for being an Exemplar.

    Using this ExemplarFilter is as good as disabling Exemplar feature.

    Reference:
        https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md#alwaysoff
    """

    def should_sample(
        self,
        value: float,
        time_unix_nano: int,
        attributes: Attributes,
        context: Context,
    ) -> bool:
        """Returns whether or not a reservoir should attempt to filter a measurement.

        Args:
            value: The value of the measurement
            time_unix_nano: A timestamp that best represents when the
                measurement was taken
            attributes: The complete set of measurement attributes
            context: The Context of the measurement

        Returns:
            ``False``, whatever the arguments are. No argument is read and
            no reservoir is ever offered a measurement.
        """
        return False


class TraceBasedExemplarFilter(ExemplarFilter):
    """An ExemplarFilter which makes those measurements eligible for being an Exemplar,
    which are recorded in the context of a sampled parent span.

    Reference:
        https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md#tracebased
    """

    def should_sample(
        self,
        value: float,
        time_unix_nano: int,
        attributes: Attributes,
        context: Context,
    ) -> bool:
        """Returns whether or not a reservoir should attempt to filter a measurement.

        Args:
            value: The value of the measurement
            time_unix_nano: A timestamp that best represents when the
                measurement was taken
            attributes: The complete set of measurement attributes
            context: The Context of the measurement. This is the only
                argument read; the other three are ignored.

        Returns:
            ``True`` when a span is current in ``context`` and the
            ``sampled`` bit of its trace flags is set. ``False`` when no
            span is current, which ``get_current_span`` reports by handing
            back ``INVALID_SPAN``, and ``False`` when the current span is
            not sampled. The decision is the span's own sampling decision,
            so a measurement recorded outside any span never becomes an
            exemplar under this filter.
        """
        span = trace.get_current_span(context)
        if span == INVALID_SPAN:
            return False
        return span.get_span_context().trace_flags.sampled
