# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Note: This package is not named "flask" because of
# https://github.com/PyCQA/pylint/issues/2648

"""
This library builds on the OpenTelemetry WSGI middleware to track web requests
in Flask applications. In addition to opentelemetry-ext-wsgi, it supports
flask-specific features such as:

* The Flask endpoint name is used as the Span name.
* The ``http.route`` Span attribute is set so that one can see which URL rule
  matched a request.

Usage
-----

.. code-block:: python

    from flask import Flask
    from opentelemetry.ext.flask import FlaskInstrumentor

    app = Flask(__name__)

    FlaskInstrumentor().instrument(app=app)

    @app.route("/")
    def hello():
        return "Hello!"

    if __name__ == "__main__":
        app.run(debug=True)

API
---
"""

from logging import getLogger

import flask

import opentelemetry.ext.wsgi as otel_wsgi
from opentelemetry import configuration, context, propagators, trace
from opentelemetry.auto_instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.ext.flask.version import __version__
from opentelemetry.util import (
    disable_tracing_hostname,
    disable_tracing_path,
    time_ns,
)

_logger = getLogger(__name__)

_ENVIRON_STARTTIME_KEY = "opentelemetry-flask.starttime_key"
_ENVIRON_SPAN_KEY = "opentelemetry-flask.span_key"
_ENVIRON_ACTIVATION_KEY = "opentelemetry-flask.activation_key"
_ENVIRON_TOKEN = "opentelemetry-flask.token"


def _rewrapped_app(wsgi_app):
    def _wrapped_app(environ, start_response):
        # We want to measure the time for route matching, etc.
        # In theory, we could start the span here and use
        # update_name later but that API is "highly discouraged" so
        # we better avoid it.
        environ[_ENVIRON_STARTTIME_KEY] = time_ns()

        def _start_response(status, response_headers, *args, **kwargs):
            span = flask.request.environ.get(_ENVIRON_SPAN_KEY)

            if span:
                otel_wsgi.add_response_attributes(
                    span, status, response_headers
                )
            else:
                _logger.warning(
                    "Flask environ's OpenTelemetry span "
                    "missing at _start_response(%s)",
                    status,
                )

            return start_response(status, response_headers, *args, **kwargs)

        return wsgi_app(environ, _start_response)

    return _wrapped_app


def _before_request():
    environ = flask.request.environ
    span_name = flask.request.endpoint or otel_wsgi.get_default_span_name(
        environ
    )
    token = context.attach(
        propagators.extract(otel_wsgi.get_header_from_environ, environ)
    )

    tracer = trace.get_tracer(__name__, __version__)

    attributes = otel_wsgi.collect_request_attributes(environ)
    if flask.request.url_rule:
        # For 404 that result from no route found, etc, we
        # don't have a url_rule.
        attributes["http.route"] = flask.request.url_rule.rule
    span = tracer.start_span(
        span_name,
        kind=trace.SpanKind.SERVER,
        attributes=attributes,
        start_time=environ.get(_ENVIRON_STARTTIME_KEY),
    )
    activation = tracer.use_span(span, end_on_exit=True)
    activation.__enter__()
    environ[_ENVIRON_ACTIVATION_KEY] = activation
    environ[_ENVIRON_SPAN_KEY] = span
    environ[_ENVIRON_TOKEN] = token


def _teardown_request(exc):
    activation = flask.request.environ.get(_ENVIRON_ACTIVATION_KEY)
    if not activation:
        _logger.warning(
            "Flask environ's OpenTelemetry activation missing"
            "at _teardown_flask_request(%s)",
            exc,
        )
        return

    if exc is None:
        activation.__exit__(None, None, None)
    else:
        activation.__exit__(
            type(exc), exc, getattr(exc, "__traceback__", None)
        )
    context.detach(flask.request.environ.get(_ENVIRON_TOKEN))


class _InstrumentedFlask(flask.Flask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._original_wsgi_ = self.wsgi_app
        self.wsgi_app = _rewrapped_app(self.wsgi_app)

        self.before_request(_before_request)
        self.teardown_request(_teardown_request)


def _disable_trace(url):
    excluded_hosts = configuration.Configuration().FLASK_EXCLUDED_HOSTS
    excluded_paths = configuration.Configuration().FLASK_EXCLUDED_PATHS
    if excluded_hosts:
        excluded_hosts = str.split(excluded_hosts, ",")
        if disable_tracing_hostname(url, excluded_hosts):
            return True
    if excluded_paths:
        excluded_paths = str.split(excluded_paths, ",")
        if disable_tracing_path(url, excluded_paths):
            return True
    return False


class FlaskInstrumentor(BaseInstrumentor):
    # pylint: disable=protected-access,attribute-defined-outside-init
    """A instrumentor for flask.Flask

    See `BaseInstrumentor`
    """

    def _instrument(self, **kwargs):
        self._original_flask = flask.Flask
        flask.Flask = _InstrumentedFlask

    def instrument_app(self, app):
        # FIXME remove this protection once some mechanism in the
        # BaseInstrumentor class is available for these methods.
        if not self._is_instrumented:
            app._original_wsgi_app = app.wsgi_app
            app.wsgi_app = _rewrapped_app(app.wsgi_app)

            app.before_request(_before_request)
            app.teardown_request(_teardown_request)
            self._is_instrumented = True
        else:
            _logger.warning(
                "Attempting to instrument while already instrumented"
            )

    def _uninstrument(self, **kwargs):
        flask.Flask = self._original_flask

    def uninstrument_app(self, app):
        # FIXME remove this protection once some mechanism in the
        # BaseInstrumentor class is available for these methods.
        if self._is_instrumented:
            app.wsgi_app = app._original_wsgi_app

            # FIXME add support for other Flask blueprints that are not None
            app.before_request_funcs[None].remove(_before_request)
            app.teardown_request_funcs[None].remove(_teardown_request)
            del app._original_wsgi_app

            self._is_instrumented = False
        else:
            _logger.warning(
                "Attempting to uninstrument while already uninstrumented"
            )
