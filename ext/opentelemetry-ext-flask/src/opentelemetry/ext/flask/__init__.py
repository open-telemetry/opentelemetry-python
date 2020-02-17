# Note: This package is not named "flask" because of
# https://github.com/PyCQA/pylint/issues/2648

import logging

from flask import request as flask_request

import opentelemetry.ext.wsgi as otel_wsgi
from opentelemetry import propagators, trace
from opentelemetry.ext.flask.version import __version__
from opentelemetry.util import time_ns

logger = logging.getLogger(__name__)


def instrument_app(flask):
    """Makes the passed-in Flask object traced by OpenTelemetry.

    You must not call this function multiple times on the same Flask object.
    """
    wsgi = flask.wsgi_app
    tracer = trace.tracer_source().get_tracer(__name__, __version__)

    def wrapped_app(environ, start_response):
        def _start_response(status, response_headers, *args, **kwargs):
            span = tracer.get_current_span()
            if span:
                otel_wsgi.add_response_attributes(
                    span.status, response_headers
                )
            else:
                logger.warning(
                    "Flask environ's OpenTelemetry span missing at _start_response(%s)",
                    status,
                )
            return start_response(status, response_headers, *args, **kwargs)

        try:
            iterable = wsgi(environ, _start_response)
            for yielded in iterable:
                yield yielded
        except Exception as error:  # noqa
            # TODO Set span status (cf. https://github.com/open-telemetry/opentelemetry-python/issues/292)
            span = tracer.get_current_span()
            if span:
                span.set_status(
                    trace.status.Status(
                        trace.status.StatusCanonicalCode.UNKNOWN,
                        description="{}: {}".format(
                            type(error).__name__, error
                        ),
                    )
                )
            raise
        finally:
            close = getattr(iterable, "close", None)
            if close:
                close()
            span = tracer.get_current_span()
            if span:
                span.end()

    def _before_flask_request():
        environ = flask_request.environ
        span_name = flask_request.endpoint or otel_wsgi.get_default_span_name(
            environ
        )
        parent_span = propagators.extract(
            otel_wsgi.get_header_from_environ, environ
        )

        span = tracer.start_span(
            span_name,
            parent_span,
            kind=trace.SpanKind.SERVER,
            attributes=otel_wsgi.collect_request_attributes(environ),
        )

        if flask_request.url_rule:
            # For 404 that result from no route found, etc, we don't have a url_rule.
            span.set_attribute("http.route", flask_request.url_rule.rule)

        activation = tracer.use_span(span, end_on_exit=True)
        activation.__enter__()

    flask.wsgi_app = wrapped_app
    flask.before_request(_before_flask_request)
