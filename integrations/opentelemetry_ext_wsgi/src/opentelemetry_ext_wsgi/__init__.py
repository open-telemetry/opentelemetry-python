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
The opentelemetry_ext_wsgi package provides a WSGI middleware that can be used
on any WSGI framework (such as Django / Flask) to track requests timing through
OpenTelemetry.
"""

import functools
import opentelemetry.trace as trace
import wsgiref.util as wsgiref_util


class OpenTelemetryMiddleware:
    """The WSGI application middleware.

    This class is used to create and annotate spans for requests to a WSGI
    application.

    :param wsgi: The WSGI application callable.
    """

    def __init__(self, wsgi, span_context_propagator=None, distributed_context_propagator=None):
        self.wsgi = wsgi

        # TODO: implement context propagation
        self.span_context_propagator = span_context_propagator
        self.distributed_context_propagator = distributed_context_propagator

    @staticmethod
    def _add_request_attributes(span, environ):
        span.set_attribute("component", "http")
        span.set_attribute("http.method", environ["REQUEST_METHOD"])
        span.set_attribute("http.path", environ["PATH_INFO"])

        host = environ.get("HTTP_HOST") or environ["SERVER_NAME"]
        span.set_attribute("http.host", host)

        url = (
            environ.get("REQUEST_URI")
            or environ.get("RAW_URI")
            or wsgiref_util.request_uri(environ, include_query=False)
        )
        span.set_attribute("http.url", url)

    @staticmethod
    def _add_response_attributes(span, status, response_headers):
        status_code, status_text = status.split(" ", 1)
        span.set_attribute("http.status_text", status_text)

        try:
            status_code = int(status_code)
        except ValueError:
            pass
        else:
            span.set_attribute("http.status_code", status_code)

    @classmethod
    def _create_start_response(cls, start_response, span):
        @functools.wraps(start_response)
        def _start_response(status, response_headers, *args):
            cls._add_response_attributes(span, status, response_headers)
            return start_response(status, response_headers, *args)

        return _start_response

    def __call__(self, environ, start_response):
        """The WSGI application

        :param environ: A WSGI environment.
        :param start_response: The WSGI start_response callable.
        """

        tracer = trace.tracer()
        method = environ["REQUEST_METHOD"]
        path = environ["PATH_INFO"]

        span_name = "[{}]{}".format(method, path)

        with tracer.start_span(span_name) as span:
            self._add_request_attributes(span, environ)
            start_response = self._create_start_response(start_response, span)

            for yielded in self.wsgi(environ, start_response):
                yield yielded
