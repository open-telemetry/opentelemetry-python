# Copyright 2019, OpenTelemetry Authors
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
The opentelemetry-ext-wsgi package provides a WSGI middleware that can be used
on any WSGI framework (such as Django / Flask) to track requests timing through
OpenTelemetry.
"""

import functools
import typing
import wsgiref.util as wsgiref_util

from opentelemetry import propagators, trace
from opentelemetry.ext.wsgi.version import __version__
from opentelemetry.util import time_ns


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


def add_request_attributes(span, environ):
    """Adds HTTP request attributes from the PEP3333-conforming WSGI environ to span."""

    span.set_attribute("component", "http")
    span.set_attribute("http.method", environ["REQUEST_METHOD"])

    host = environ.get("HTTP_HOST")
    if not host:
        host = environ["SERVER_NAME"]
        port = environ["SERVER_PORT"]
        scheme = environ["wsgi.url_scheme"]
        if (
            scheme == "http"
            and port != "80"
            or scheme == "https"
            and port != "443"
        ):
            host += ":" + port

    # NOTE: Nonstandard (but see
    # https://github.com/open-telemetry/opentelemetry-specification/pull/263)
    span.set_attribute("http.host", host)

    url = environ.get("REQUEST_URI") or environ.get("RAW_URI")

    if url:
        if url[0] == "/":
            # We assume that no scheme-relative URLs will be in url here.
            # After all, if a request is made to http://myserver//foo, we may get
            # //foo which looks like scheme-relative but isn't.
            url = environ["wsgi.url_scheme"] + "://" + host + url
        elif not url.startswith(environ["wsgi.url_scheme"] + ":"):
            # Something fishy is in RAW_URL. Let's fall back to request_uri()
            url = wsgiref_util.request_uri(environ)
    else:
        url = wsgiref_util.request_uri(environ)

    span.set_attribute("http.url", url)


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
        pass
    else:
        span.set_attribute("http.status_code", status_code)


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
        self.tracer = trace.tracer_source().get_tracer(
            "opentelemetry-ext-wsgi", __version__
        )

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

        start_timestamp = time_ns()

        parent_span = propagators.extract(get_header_from_environ, environ)
        span_name = get_default_span_name(environ)

        span = self.tracer.create_span(
            span_name, parent_span, kind=trace.SpanKind.SERVER
        )
        span.start(start_timestamp)

        try:
            with self.tracer.use_span(span):
                add_request_attributes(span, environ)
                start_response = self._create_start_response(
                    span, start_response
                )
                iterable = self.wsgi(environ, start_response)
                return _end_span_after_iterating(iterable, span, self.tracer)
        except:  # noqa
            span.end()
            raise


# Put this in a subfunction to not delay the call to the wrapped
# WSGI application (instrumentation should change the application
# behavior as little as possible).
def _end_span_after_iterating(iterable, span, tracer):
    try:
        with tracer.use_span(span):
            for yielded in iterable:
                yield yielded
    finally:
        close = getattr(iterable, "close", None)
        if close:
            close()
        span.end()
