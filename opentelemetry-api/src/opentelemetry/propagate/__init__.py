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

``OTEL_PROPAGATORS`` is read on the first call to ``get_global_textmap()``
(and therefore on the first ``extract`` or ``inject``), not when this module
is imported. A distro can import the API and then set the variable from
``configure()``. ``set_global_textmap()`` always wins over the environment
variable, including when it is called before that first read. A failed load
is not cached, so a later call can succeed after the variable is corrected.

Example::

    import flask
    import requests
    from opentelemetry import propagate


    PROPAGATOR = propagate.get_global_textmap()


    def get_header_from_flask_request(request, key):
        return request.headers.get_all(key)


    def set_header_into_requests_request(request: requests.Request, key: str, value: str):
        request.headers[key] = value


    def example_route():
        context = PROPAGATOR.extract(get_header_from_flask_request, flask.request)
        request_to_downstream = requests.Request("GET", "http://httpbin.org/get")
        PROPAGATOR.inject(
            set_header_into_requests_request,
            request_to_downstream,
            context=context,
        )
        session = requests.Session()
        session.send(request_to_downstream.prepare())


.. _Propagation API Specification:
    https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/context/api-propagators.md
"""

from logging import getLogger
from os import environ
from threading import Lock

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


# None means "not loaded yet". Resolved on the first get_global_textmap() so a
# distro can set OTEL_PROPAGATORS in configure() after this module is imported.
# set_global_textmap() stores a real propagator and therefore wins over a later
# read of the environment variable. Reloading this module clears the cache.
_HTTP_TEXT_FORMAT: textmap.TextMapPropagator | None = None
_HTTP_TEXT_FORMAT_LOCK = Lock()

# Deprecated: propagators, environ_propagators and propagator names were never intendended to be part of the public API.
propagators: list[textmap.TextMapPropagator] = []

environ_propagators = environ.get(OTEL_PROPAGATORS, "tracecontext,baggage")

for propagator in environ_propagators.split(","):  # type: ignore[assignment]
    propagator = propagator.strip()


def get_global_textmap() -> textmap.TextMapPropagator:
    """Return the global text map propagator, loading it on first use.

    The first call reads ``OTEL_PROPAGATORS``. Later calls return the same
    instance until ``set_global_textmap()`` replaces it or this module is
    reloaded. A load that raises does not fill the cache.

    Propagators are constructed outside the lock so a propagator ``__init__``
    that calls back into this function cannot deadlock. ``set_global_textmap()``
    during that construction still wins.
    """
    current = _HTTP_TEXT_FORMAT
    if current is not None:
        return current

    with _HTTP_TEXT_FORMAT_LOCK:
        current = _HTTP_TEXT_FORMAT
        if current is not None:
            return current

    loaded = _load_propagators()
    with _HTTP_TEXT_FORMAT_LOCK:
        # set_global_textmap() may have stored an explicit propagator while the
        # entry points were loading. Keep that one.
        current = _HTTP_TEXT_FORMAT
        if current is None:
            _set_global_textmap(loaded)
            return loaded
        return current


def set_global_textmap(
    http_text_format: textmap.TextMapPropagator,
) -> None:
    """Set the global text map propagator.

    Takes precedence over ``OTEL_PROPAGATORS``, whether or not that variable
    has already been read.
    """
    with _HTTP_TEXT_FORMAT_LOCK:
        _set_global_textmap(http_text_format)


def _set_global_textmap(http_text_format: textmap.TextMapPropagator) -> None:
    global _HTTP_TEXT_FORMAT  # pylint:disable=global-statement
    _HTTP_TEXT_FORMAT = http_text_format
