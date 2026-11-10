# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""
API for propagation of context.

The propagators for the
``opentelemetry.propagators.composite.CompositePropagator`` can be defined
via configuration in the ``OTEL_PROPAGATORS`` environment variable. This
variable should be set to a comma-separated string of names of values for the
``opentelemetry_propagator`` entry point. For example, setting
``OTEL_PROPAGATORS`` to ``tracecontext,baggage`` (which is the default value)
would instantiate
``opentelemetry.propagators.composite.CompositePropagator`` with 2
propagators, one of type
``opentelemetry.trace.propagation.tracecontext.TraceContextTextMapPropagator``
and other of type ``opentelemetry.baggage.propagation.W3CBaggagePropagator``.
Notice that these propagator classes are defined as
``opentelemetry_propagator`` entry points in the ``pyproject.toml`` file of
``opentelemetry``.

See the `Propagation API Specification`_ for what a propagator has to do.

Example::

    import flask
    import requests
    from opentelemetry import propagate
    from opentelemetry.propagators.textmap import Getter, Setter


    PROPAGATOR = propagate.get_global_textmap()


    class FlaskGetter(Getter[flask.Request]):
        def get(self, carrier: flask.Request, key: str) -> list[str] | None:
            return carrier.headers.get_all(key) or None

        def keys(self, carrier: flask.Request) -> list[str]:
            return list(carrier.headers.keys())


    class RequestsSetter(Setter[requests.Request]):
        def set(self, carrier: requests.Request, key: str, value: str) -> None:
            carrier.headers[key] = value


    def example_route() -> None:
        context = PROPAGATOR.extract(flask.request, getter=FlaskGetter())
        request_to_downstream = requests.Request("GET", "http://httpbin.org/get")
        PROPAGATOR.inject(
            request_to_downstream,
            context=context,
            setter=RequestsSetter(),
        )
        session = requests.Session()
        session.send(request_to_downstream.prepare())


.. _Propagation API Specification:
    https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/context/api-propagators.md
"""

from logging import getLogger
from os import environ

from opentelemetry.context.context import Context
from opentelemetry.environment_variables import OTEL_PROPAGATORS
from opentelemetry.propagators import composite, textmap

logger = getLogger(__name__)


def extract(
    carrier: textmap.CarrierT,
    context: Context | None = None,
    getter: textmap.Getter[textmap.CarrierT] = textmap.default_getter,
) -> Context:
    """Uses the configured propagator to extract a Context from the carrier.

    Args:
        getter: an object which contains a get function that can retrieve zero
            or more values from the carrier and a keys function that can get all the keys
            from carrier.
        carrier: and object which contains values that are
            used to construct a Context. This object
            must be paired with an appropriate getter
            which understands how to extract a value from it.
        context: an optional Context to use. Defaults to root
            context if not set.

    Returns:
        A Context holding whatever the globally configured propagator found in
        the carrier. When the carrier holds nothing the propagator recognises,
        ``context`` is returned unchanged.
    """
    return get_global_textmap().extract(carrier, context, getter=getter)


def inject(
    carrier: textmap.CarrierT,
    context: Context | None = None,
    setter: textmap.Setter[textmap.CarrierT] = textmap.default_setter,
) -> None:
    """Uses the configured propagator to inject a Context into the carrier.

    Args:
        carrier: the medium used by Propagators to read
            values from and write values to.
            Should be paired with setter, which
            should know how to set header values on the carrier.
        context: An optional Context to use. Defaults to current
            context if not set.
        setter: An optional `Setter` object that can set values
            on the carrier.
    """
    get_global_textmap().inject(carrier, context=context, setter=setter)


def _load_propagators() -> textmap.TextMapPropagator:
    """Build the global propagator from the ``OTEL_PROPAGATORS`` variable.

    Each comma-separated name is loaded as an ``opentelemetry_propagator``
    entry point. When the variable is unset, W3C trace context and W3C baggage
    are used. When a name is ``none``, propagation is disabled entirely and
    every name after it is ignored. Every name before it is resolved first, so
    a misspelled name ahead of ``none`` still raises :exc:`ValueError`.

    Returns:
        A :class:`~opentelemetry.propagators.composite.CompositePropagator`
        wrapping the configured propagators, in the order they were named. It
        wraps an empty list when propagation is disabled.

    Raises:
        ValueError: If a named propagator has no matching entry point, which
            means it is misspelled or its package is not installed.
        Exception: Re-raises whatever loading an entry point raised, after
            logging it.
    """
    configured = environ.get(OTEL_PROPAGATORS)
    if not configured:
        # pylint: disable=import-outside-toplevel,no-name-in-module
        from opentelemetry.baggage.propagation import (  # noqa: PLC0415
            W3CBaggagePropagator,
        )

        # pylint: disable=import-outside-toplevel,no-name-in-module
        from opentelemetry.trace.propagation.tracecontext import (  # noqa: PLC0415
            TraceContextTextMapPropagator,
        )

        return composite.CompositePropagator([TraceContextTextMapPropagator(), W3CBaggagePropagator()])

    # pylint: disable=import-outside-toplevel,no-name-in-module
    from opentelemetry.util._importlib_metadata import (  # noqa: PLC0415
        entry_points,
    )

    _propagators: list[textmap.TextMapPropagator] = []
    for _propagator in configured.split(","):
        _propagator = _propagator.strip()
        if _propagator.lower() == "none":
            logger.debug("OTEL_PROPAGATORS environment variable contains none, removing all propagators")
            return composite.CompositePropagator([])
        try:
            _propagators.append(
                next(  # type: ignore
                    iter(  # type: ignore
                        entry_points(  # type: ignore[misc]
                            group="opentelemetry_propagator",
                            name=_propagator,
                        )
                    )
                ).load()()
            )
        except StopIteration:
            raise ValueError(f"Propagator {_propagator} not found. It is either misspelled or not installed.")
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Failed to load propagator: %s", _propagator)
            raise
    return composite.CompositePropagator(_propagators)


_HTTP_TEXT_FORMAT: textmap.TextMapPropagator = _load_propagators()

# Deprecated: propagators, environ_propagators and propagator names were never intendended to be part of the public API.
propagators: list[textmap.TextMapPropagator] = []

environ_propagators = environ.get(OTEL_PROPAGATORS, "tracecontext,baggage")

for propagator in environ_propagators.split(","):  # type: ignore[assignment]
    propagator = propagator.strip()


def get_global_textmap() -> textmap.TextMapPropagator:
    """Return the propagator that :func:`extract` and :func:`inject` use.

    Returns:
        The globally configured propagator. Unless
        :func:`set_global_textmap` has replaced it, this is the one built from
        the ``OTEL_PROPAGATORS`` environment variable at import time.
    """
    return _HTTP_TEXT_FORMAT


def set_global_textmap(
    http_text_format: textmap.TextMapPropagator,
) -> None:
    """Replace the propagator that :func:`extract` and :func:`inject` use.

    This overrides whatever the ``OTEL_PROPAGATORS`` environment variable
    selected. Call it before any instrumentation starts propagating, since a
    propagator already captured by a caller is not replaced.

    Args:
        http_text_format: The propagator to install globally.
    """
    global _HTTP_TEXT_FORMAT  # pylint:disable=global-statement
    _HTTP_TEXT_FORMAT = http_text_format
