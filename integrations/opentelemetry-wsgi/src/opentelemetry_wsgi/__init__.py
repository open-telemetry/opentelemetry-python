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
The opentelemetry_wsgi integration provides a WSGI middleware that can be used
on any WSGI framework (such as Django / Flask) to track requests timing through
OpenTelemetry.
"""

import opentelemetry.trace as trace


class OpenTelemetryMiddleware:
    """The WSGI application middleware.

    This class is used to create and annotate spans for requests to a WSGI
    application.

    :param wsgi: The WSGI application callable.
    """

    def __init__(self, wsgi):
        self.wsgi = wsgi
        self.start_response = None
        self.span = None

    def _add_request_attributes(self, environ):
        self.span.add_attribute("http.method", environ["REQUEST_METHOD"])
        self.span.add_attribute("http.path", environ["PATH_INFO"])
        self.span.add_attribute("http.route", environ["PATH_INFO"])

        host = environ.get("HTTP_HOST") or environ.get("SERVER_NAME")
        if host is not None:
            self.span.add_attribute("http.host", host)

        url = environ.get("REQUEST_URI") or environ.get("RAW_URI")
        if url is not None:
            self.span.add_attribute("http.url", url)

    def _add_response_attributes(self, status, response_headers, *args):
        try:
            status_code = int(status.split(" ", 1)[0])
            self.span.add_attribute("http.status_code", status_code)
        except ValueError:
            pass

        return self.start_response(status, response_headers, *args)

    def __call__(self, environ, start_response):
        """The WSGI application

        :param environ: A WSGI environment.
        :param start_response: The WSGI start_response callable.
        """
        self.start_response = start_response

        tracer = trace.tracer()
        method = environ["REQUEST_METHOD"]
        path = environ["PATH_INFO"]

        span_name = "[{}]{}".format(method, path)

        with tracer.start_span(span_name) as span:
            self.span = span
            # TODO: enable request attributes after set_attribute API is
            # implemented
            # self._add_request_attributes(environ)

            # TODO: change start_response to self._add_response_attributes after
            # set_attribute API is implemented
            for yielded in self.wsgi(environ, start_response):
                yield yielded
