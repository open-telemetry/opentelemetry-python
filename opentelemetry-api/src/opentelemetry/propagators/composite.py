# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
"""A propagator that chains several other propagators together.

An application usually needs more than one wire format at once, for example
W3C trace context together with W3C baggage.
:class:`CompositePropagator` presents several propagators as one. It is what
:func:`opentelemetry.propagate.get_global_textmap` returns in every case, since
``OTEL_PROPAGATORS`` naming a single propagator still produces a
:class:`CompositePropagator` wrapping that one, and naming ``none`` produces
one wrapping no propagator at all.
"""

import collections.abc
import logging

from typing_extensions import deprecated

from opentelemetry.context.context import Context
from opentelemetry.propagators import textmap

logger = logging.getLogger(__name__)


class CompositePropagator(textmap.TextMapPropagator):
    """CompositePropagator provides a mechanism for combining multiple
    propagators into a single one.

    Args:
        propagators: the list of propagators to use
    """

    def __init__(self, propagators: collections.abc.Sequence[textmap.TextMapPropagator]) -> None:
        """Store the propagators to run, in the order given.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._propagators = propagators

    def extract(
        self,
        carrier: textmap.CarrierT,
        context: Context | None = None,
        getter: textmap.Getter[textmap.CarrierT] = textmap.default_getter,
    ) -> Context:
        """Run each of the configured propagators with the given context and carrier.
        Propagators are run in the order they are configured, if multiple
        propagators write the same context key, the propagator later in the list
        will override previous propagators.

        See `opentelemetry.propagators.textmap.TextMapPropagator.extract`

        Args:
            carrier: The object holding the incoming values, passed unchanged
                to every configured propagator.
            context: The context to add the extracted values to. ``None`` is
                handed to the first configured propagator only, which decides
                what to use in its place. Every later propagator receives the
                context the previous propagator returned.
            getter: Reads values out of ``carrier``, passed unchanged to every
                configured propagator.

        Returns:
            The context returned by the last configured propagator, having
            been threaded through each one in turn. When no propagator is
            configured, ``context`` is returned unchanged.
        """
        for propagator in self._propagators:
            context = propagator.extract(carrier, context, getter=getter)
        return context  # type: ignore

    def inject(
        self,
        carrier: textmap.CarrierT,
        context: Context | None = None,
        setter: textmap.Setter[textmap.CarrierT] = textmap.default_setter,
    ) -> None:
        """Run each of the configured propagators with the given context and carrier.
        Propagators are run in the order they are configured, if multiple
        propagators write the same carrier key, the propagator later in the list
        will override previous propagators.

        See `opentelemetry.propagators.textmap.TextMapPropagator.inject`

        Args:
            carrier: The object to write the outgoing values into, passed
                unchanged to every configured propagator.
            context: The context to read the values from. If ``None``, each
                propagator falls back to the current context.
            setter: Writes values into ``carrier``, passed unchanged to every
                configured propagator.
        """
        for propagator in self._propagators:
            propagator.inject(carrier, context, setter=setter)

    @property
    def fields(self) -> set[str]:
        """Returns a set with the fields set in `inject`.

        See
        `opentelemetry.propagators.textmap.TextMapPropagator.fields`

        Returns:
            The union of the fields of every configured propagator.
        """
        composite_fields = set()

        for propagator in self._propagators:
            for field in propagator.fields:
                composite_fields.add(field)

        return composite_fields


@deprecated("You should use CompositePropagator. Deprecated since version 1.2.0.")
class CompositeHTTPPropagator(CompositePropagator):
    """CompositeHTTPPropagator provides a mechanism for combining multiple
    propagators into a single one.
    """
