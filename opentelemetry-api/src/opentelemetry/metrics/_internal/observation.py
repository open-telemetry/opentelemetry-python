# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""A single measurement reported by an asynchronous instrument."""

from opentelemetry.context import Context
from opentelemetry.util.types import Attributes


class Observation:
    """A measurement observed in an asynchronous instrument

    Return/yield instances of this class from asynchronous instrument callbacks.

    Args:
        value: The float or int measured value
        attributes: The measurement's attributes
        context: The measurement's context
    """

    def __init__(
        self,
        value: float,
        attributes: Attributes = None,
        context: Context | None = None,
    ) -> None:
        """Record one measurement to be reported by a callback.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._value = value
        self._attributes = attributes
        self._context = context

    @property
    def value(self) -> float | int:
        """The measured value.

        Returns:
            The value this observation was built with.
        """
        return self._value

    @property
    def attributes(self) -> Attributes:
        """The attributes the measurement is recorded under.

        Returns:
            The attributes, or ``None`` when the observation carries none.
            Each distinct set of attributes forms its own time series.
        """
        return self._attributes

    @property
    def context(self) -> Context | None:
        """The context the measurement was taken in.

        Returns:
            The context, or ``None`` when the observation carries none. It is
            what lets an exemplar link the measurement back to a span.
        """
        return self._context

    def __eq__(self, other: object) -> bool:
        """Compare against another observation by value, attributes and context.

        Args:
            other: The object to compare with.

        Returns:
            ``True`` when ``other`` is an :class:`Observation` whose value,
            attributes and context are all equal to this one's.
        """
        return (
            isinstance(other, Observation)
            and self.value == other.value
            and self.attributes == other.attributes
            and self.context == other.context
        )

    def __repr__(self) -> str:
        """Render the observation for debugging.

        Returns:
            A string naming the value, the attributes and the context.
        """
        return f"Observation(value={self.value}, attributes={self.attributes}, context={self.context})"
