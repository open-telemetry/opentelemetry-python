# Note: This package is not named "flask" because of
# https://github.com/PyCQA/pylint/issues/2648

import logging

from flask import request as flask_request

import opentelemetry.ext.wsgi as otel_wsgi
from opentelemetry import propagators, trace
from opentelemetry.ext.flask.version import __version__
from opentelemetry.util import time_ns

logger = logging.getLogger(__name__)

_ENVIRON_STARTTIME_KEY = object()
_ENVIRON_SPAN_KEY = object()
_ENVIRON_ACTIVATION_KEY = object()


def instrument_app(flask):
    """Makes the passed-in Flask object traced by OpenTelemetry.

    You must not call this function multiple times on the same Flask object.
    """

    wsgi = flask.wsgi_app

    def wrapped_app(environ, start_response):
        # We want to measure the time for route matching, etc.
        # In theory, we could start the span here and use update_name later
        # but that API is "highly discouraged" so we better avoid it.
        environ[_ENVIRON_STARTTIME_KEY] = time_ns()

        def _start_response(status, response_headers, *args, **kwargs):
            span = flask_request.environ.get(_ENVIRON_SPAN_KEY)
            if span:
                otel_wsgi.add_response_attributes(
                    span, status, response_headers
                )
            else:
                logger.warning(
                    "Flask environ's OpenTelemetry span missing at _start_response(%s)",
                    status,
                )
            return start_response(status, response_headers, *args, **kwargs)

        return wsgi(environ, _start_response)

    flask.wsgi_app = wrapped_app

    flask.before_request(_before_flask_request)
    flask.teardown_request(_teardown_flask_request)


def _before_flask_request():
    environ = flask_request.environ
    span_name = flask_request.endpoint or otel_wsgi.get_default_span_name(
        environ
    )
    parent_span = propagators.extract(
        otel_wsgi.get_header_from_environ, environ
    )

    tracer = trace.tracer_source().get_tracer(
        "opentelemetry-ext-flask", __version__
    )

    attributes = otel_wsgi.collect_request_attributes(environ)
    if flask_request.url_rule:
        # For 404 that result from no route found, etc, we don't have a url_rule.
        attributes["http.route"] = flask_request.url_rule.rule
    span = tracer.start_span(
        span_name,
        parent_span,
        kind=trace.SpanKind.SERVER,
        attributes=attributes,
        start_time=environ.get(_ENVIRON_STARTTIME_KEY),
    )
    activation = tracer.use_span(span, end_on_exit=True)
    activation.__enter__()
    environ[_ENVIRON_ACTIVATION_KEY] = activation
    environ[_ENVIRON_SPAN_KEY] = span


def _teardown_flask_request(exc):
    activation = flask_request.environ.get(_ENVIRON_ACTIVATION_KEY)
    if not activation:
        logger.warning(
            "Flask environ's OpenTelemetry activation missing at _teardown_flask_request(%s)",
            exc,
        )
        return

    if exc is None:
        activation.__exit__(None, None, None)
    else:
        activation.__exit__(
            type(exc), exc, getattr(exc, "__traceback__", None)
        )
