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

"""
This library provides a WSGI middleware that can be used on any WSGI framework
(such as Django / Flask) to track requests timing through OpenTelemetry.

Usage (Flask)
-------------

.. code-block:: python

    from flask import Flask
    from opentelemetry.ext.wsgi import OpenTelemetryMiddleware

    app = Flask(__name__)
    app.wsgi_app = OpenTelemetryMiddleware(app.wsgi_app)

    @app.route("/")
    def hello():
        return "Hello!"

    if __name__ == "__main__":
        app.run(debug=True)


Usage (Django)
--------------

Modify the application's ``wsgi.py`` file as shown below.

.. code-block:: python

    import os
    from opentelemetry.ext.wsgi import OpenTelemetryMiddleware
    from django.core.wsgi import get_wsgi_application

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')

    application = get_wsgi_application()
    application = OpenTelemetryMiddleware(application)
"""

import functools
import typing
import wsgiref.util as wsgiref_util

from opentelemetry import context, propagators, trace
from opentelemetry.ext.wsgi.version import __version__
from opentelemetry.trace.propagation import get_span_from_context
from opentelemetry.trace.status import Status, StatusCanonicalCode

_HTTP_VERSION_PREFIX = "HTTP/"


def get_header_from_environ(
    environ: dict, header_name: str
) -> typing.List[str]:
    """Retrieve a HTTP header value from the PEP3333-conforming WSGI environ.

    Returns:
        A list with a single string with the header value if it exists, else an empty list.
    """
    environ_key = "HTTP_" + header_name.upper().replace("-", "_")
    value = environ.get(environ_key)
    if value is not None:
        return [value]
    return []


def setifnotnone(dic, key, value):
    if value is not None:
        dic[key] = value


def http_status_to_canonical_code(code: int, allow_redirect: bool = True):
    # pylint:disable=too-many-branches,too-many-return-statements
    if code < 100:
        return StatusCanonicalCode.UNKNOWN
    if code <= 299:
        return StatusCanonicalCode.OK
    if code <= 399:
        if allow_redirect:
            return StatusCanonicalCode.OK
        return StatusCanonicalCode.DEADLINE_EXCEEDED
    if code <= 499:
        if code == 401:  # HTTPStatus.UNAUTHORIZED:
            return StatusCanonicalCode.UNAUTHENTICATED
        if code == 403:  # HTTPStatus.FORBIDDEN:
            return StatusCanonicalCode.PERMISSION_DENIED
        if code == 404:  # HTTPStatus.NOT_FOUND:
            return StatusCanonicalCode.NOT_FOUND
        if code == 429:  # HTTPStatus.TOO_MANY_REQUESTS:
            return StatusCanonicalCode.RESOURCE_EXHAUSTED
        return StatusCanonicalCode.INVALID_ARGUMENT
    if code <= 599:
        if code == 501:  # HTTPStatus.NOT_IMPLEMENTED:
            return StatusCanonicalCode.UNIMPLEMENTED
        if code == 503:  # HTTPStatus.SERVICE_UNAVAILABLE:
            return StatusCanonicalCode.UNAVAILABLE
        if code == 504:  # HTTPStatus.GATEWAY_TIMEOUT:
            return StatusCanonicalCode.DEADLINE_EXCEEDED
        return StatusCanonicalCode.INTERNAL
    return StatusCanonicalCode.UNKNOWN


def collect_request_attributes(environ):
    """Collects HTTP request attributes from the PEP3333-conforming
    WSGI environ and returns a dictionary to be used as span creation attributes."""

    result = {
        "component": "http",
        "http.method": environ["REQUEST_METHOD"],
        "http.server_name": environ["SERVER_NAME"],
        "http.scheme": environ["wsgi.url_scheme"],
        "host.port": int(environ["SERVER_PORT"]),
    }

    setifnotnone(result, "http.host", environ.get("HTTP_HOST"))
    target = environ.get("RAW_URI")
    if target is None:  # Note: `"" or None is None`
        target = environ.get("REQUEST_URI")
    if target is not None:
        result["http.target"] = target
    else:
        result["http.url"] = wsgiref_util.request_uri(environ)

    remote_addr = environ.get("REMOTE_ADDR")
    if remote_addr:
        result["net.peer.ip"] = remote_addr
    remote_host = environ.get("REMOTE_HOST")
    if remote_host and remote_host != remote_addr:
        result["net.peer.name"] = remote_host

    setifnotnone(result, "net.peer.port", environ.get("REMOTE_PORT"))
    flavor = environ.get("SERVER_PROTOCOL", "")
    if flavor.upper().startswith(_HTTP_VERSION_PREFIX):
        flavor = flavor[len(_HTTP_VERSION_PREFIX) :]
    if flavor:
        result["http.flavor"] = flavor

    return result


def add_response_attributes(
    span, start_response_status, response_headers
):  # pylint: disable=unused-argument
    """Adds HTTP response attributes to span using the arguments
    passed to a PEP3333-conforming start_response callable."""

    status_code, status_text = start_response_status.split(" ", 1)
    span.set_attribute("http.status_text", status_text)

    try:
        status_code = int(status_code)
    except ValueError:
        span.set_status(
            Status(
                StatusCanonicalCode.UNKNOWN,
                "Non-integer HTTP status: " + repr(status_code),
            )
        )
    else:
        span.set_attribute("http.status_code", status_code)
        span.set_status(Status(http_status_to_canonical_code(status_code)))


def get_default_span_name(environ):
    """Calculates a (generic) span name for an incoming HTTP request based on the PEP3333 conforming WSGI environ."""

    # TODO: Update once
    #  https://github.com/open-telemetry/opentelemetry-specification/issues/270
    #  is resolved
    return environ.get("PATH_INFO", "/")


class OpenTelemetryMiddleware:
    """The WSGI application middleware.

    This class is a PEP 3333 conforming WSGI middleware that starts and
    annotates spans for any requests it is invoked with.

    Args:
        wsgi: The WSGI application callable to forward requests to.
    """

    def __init__(self, wsgi):
        self.wsgi = wsgi
        self.tracer = trace.get_tracer(__name__, __version__)

    @staticmethod
    def _create_start_response(span, start_response):
        @functools.wraps(start_response)
        def _start_response(status, response_headers, *args, **kwargs):
            add_response_attributes(span, status, response_headers)
            return start_response(status, response_headers, *args, **kwargs)

        return _start_response

    def __call__(self, environ, start_response):
        """The WSGI application

        Args:
            environ: A WSGI environment.
            start_response: The WSGI start_response callable.
        """

        token = context.attach(
            propagators.extract(get_header_from_environ, environ)
        )
        span_name = get_default_span_name(environ)

        span = self.tracer.start_span(
            span_name,
            kind=trace.SpanKind.SERVER,
            attributes=collect_request_attributes(environ),
        )

        try:
            with self.tracer.use_span(span):
                start_response = self._create_start_response(
                    span, start_response
                )
                iterable = self.wsgi(environ, start_response)
                return _end_span_after_iterating(
                    iterable, span, self.tracer, token
                )
        except:  # noqa
            # TODO Set span status (cf. https://github.com/open-telemetry/opentelemetry-python/issues/292)
            span.end()
            context.detach(token)
            raise


# Put this in a subfunction to not delay the call to the wrapped
# WSGI application (instrumentation should change the application
# behavior as little as possible).
def _end_span_after_iterating(iterable, span, tracer, token):
    try:
        with tracer.use_span(span):
            for yielded in iterable:
                yield yielded
    finally:
        close = getattr(iterable, "close", None)
        if close:
            close()
        span.end()
        context.detach(token)
