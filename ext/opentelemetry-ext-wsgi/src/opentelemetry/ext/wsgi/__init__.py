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
from opentelemetry.ext.wsgi.version import __version__  # noqa


class OpenTelemetryMiddleware:
    """The WSGI application middleware.

    This class is used to create and annotate spans for requests to a WSGI
    application.

    Args:
        wsgi: The WSGI application callable.
    """

    def __init__(self, wsgi):
        self.wsgi = wsgi

    @staticmethod
    def _add_request_attributes(span, environ):
        span.set_attribute("component", "http")
        span.set_attribute("http.method", environ["REQUEST_METHOD"])

        host = environ.get("HTTP_HOST")
        if not host:
            host = environ["SERVER_NAME"]
            port = environ["SERVER_PORT"]
            if (
                port != "80"
                and environ["wsgi.url_scheme"] == "http"
                or port != "443"
            ):
                host += ":" + port

        # NOTE: Nonstandard
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

    @staticmethod
    def _add_response_attributes(span, status):
        status_code, status_text = status.split(" ", 1)
        span.set_attribute("http.status_text", status_text)

        try:
            status_code = int(status_code)
        except ValueError:
            pass
        else:
            span.set_attribute("http.status_code", status_code)

    @classmethod
    def _create_start_response(cls, span, start_response):
        @functools.wraps(start_response)
        def _start_response(status, response_headers, *args, **kwargs):
            cls._add_response_attributes(span, status)
            return start_response(status, response_headers, *args, **kwargs)

        return _start_response

    def __call__(self, environ, start_response):
        """The WSGI application

        Args:
            environ: A WSGI environment.
            start_response: The WSGI start_response callable.
        """

        tracer = trace.tracer()
        path_info = environ["PATH_INFO"] or "/"
        parent_span = propagators.extract(get_header_from_environ, environ)

        span = tracer.create_span(
            path_info, parent_span, kind=trace.SpanKind.SERVER
        )
        span.start()
        try:
            with tracer.use_span(span):
                self._add_request_attributes(span, environ)
                start_response = self._create_start_response(
                    span, start_response
                )

                iterable = self.wsgi(environ, start_response)

                # Put this in a subfunction to not delay the call to the wrapped
                # WSGI application (instrumentation should change the application
                # behavior as little as possible).
                def iter_result(iterable, span):
                    try:
                        with tracer.use_span(span):
                            for yielded in iterable:
                                yield yielded
                    finally:
                        close = getattr(iterable, "close", None)
                        if close:
                            close()
                        span.end()

                return iter_result(iterable, span)
        except:  # noqa
            span.end()
            raise


def get_header_from_environ(
    environ: dict, header_name: str
) -> typing.List[str]:
    """Retrieve the header value from the wsgi environ dictionary.

    Returns:
        A string with the header value if it exists, else None.
    """
    environ_key = "HTTP_" + header_name.upper().replace("-", "_")
    value = environ.get(environ_key)
    if value:
        return [value]
    return []
