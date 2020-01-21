# Note: This package is not named "flask" because of
# https://github.com/PyCQA/pylint/issues/2648

import logging

from flask import request as flask_request

import opentelemetry.ext.wsgi as otel_wsgi
from opentelemetry import propagators, trace
from opentelemetry.ext.flask.version import __version__
from opentelemetry.util import time_ns

logger = logging.getLogger(__name__)

_ENVIRON_STARTTIME_KEY = "opentelemetry-flask.starttime_key"
_ENVIRON_SPAN_KEY = "opentelemetry-flask.span_key"
_ENVIRON_ACTIVATION_KEY = "opentelemetry-flask.activation_key"


def instrument_app(flask):
    """Makes the passed-in Flask object traced by OpenTelemetry.

    You must not call this function multiple times on the same Flask object.
    """

    wsgi = flask.wsgi_app
    flask.wsgi_app = otel_wsgi.OpenTelemetryMiddleware(wsgi)
    flask.before_request(_before_flask_request)


def _before_flask_request():
    wsgi_tracer = trace.tracer_source().get_tracer(
        otel_wsgi.__name__, otel_wsgi.__version__
    )
    span = wsgi_tracer.get_current_span()
    if flask_request.endpoint:
        span.update_name(flask_request.endpoint)
    if flask_request.url_rule:
        # For 404 that result from no route found, etc, we don't have a url_rule.
        span.set_attribute("http.route", flask_request.url_rule.rule)
