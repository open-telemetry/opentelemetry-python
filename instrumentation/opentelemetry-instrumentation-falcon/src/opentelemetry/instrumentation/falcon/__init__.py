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
This library builds on the OpenTelemetry WSGI middleware to track web requests
in Falcon applications. In addition to opentelemetry-instrumentation-wsgi,
it supports falcon-specific features such as:

* The Falcon resource and method name is used as the Span name.
* The ``falcon.resource`` Span attribute is set so the matched resource.
* Error from Falcon resources are properly caught and recorded.

Usage
-----

.. code-block:: python

    from falcon import API
    from opentelemetry.instrumentation.falcon import FalconInstrumentor

    FalconInstrumentor().instrument()

    app = falcon.API()

    class HelloWorldResource(object):
        def on_get(self, req, resp):
            resp.body = 'Hello World'

    app.add_route('/hello', HelloWorldResource())

API
---
"""

import sys
from logging import getLogger

import falcon

import opentelemetry.instrumentation.wsgi as otel_wsgi
from opentelemetry import configuration, context, propagators, trace
from opentelemetry.instrumentation.falcon.version import __version__
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.instrumentation.utils import http_status_to_canonical_code
from opentelemetry.trace.status import Status
from opentelemetry.util import ExcludeList, time_ns

_logger = getLogger(__name__)

_ENVIRON_STARTTIME_KEY = "opentelemetry-falcon.starttime_key"
_ENVIRON_SPAN_KEY = "opentelemetry-falcon.span_key"
_ENVIRON_ACTIVATION_KEY = "opentelemetry-falcon.activation_key"
_ENVIRON_TOKEN = "opentelemetry-falcon.token"
_ENVIRON_EXC = "opentelemetry-falcon.exc"


def get_excluded_urls():
    urls = configuration.Configuration().FALCON_EXCLUDED_URLS or ""
    if urls:
        urls = str.split(urls, ",")
    return ExcludeList(urls)


_excluded_urls = get_excluded_urls()


class FalconInstrumentor(BaseInstrumentor):
    # pylint: disable=protected-access,attribute-defined-outside-init
    """An instrumentor for falcon.API

    See `BaseInstrumentor`
    """

    def _instrument(self, **kwargs):
        self._original_falcon_api = falcon.API
        falcon.API = _InstrumentedFalconAPI

    def _uninstrument(self, **kwargs):
        falcon.API = self._original_falcon_api


class _InstrumentedFalconAPI(falcon.API):
    def __init__(self, *args, **kwargs):
        mw = kwargs.pop("middleware", [])
        if not isinstance(mw, (list, tuple)):
            mw = [mw]

        self._tracer = trace.get_tracer(__name__, __version__)
        mw.insert(0, _TraceMiddleware(self._tracer))
        kwargs["middleware"] = mw
        super().__init__(*args, **kwargs)

    def __call__(self, env, start_response):
        if _excluded_urls.url_disabled(env.get("PATH_INFO", "/")):
            return super().__call__(env, start_response)

        start_time = time_ns()

        token = context.attach(
            propagators.extract(otel_wsgi.get_header_from_environ, env)
        )
        attributes = otel_wsgi.collect_request_attributes(env)
        span = self._tracer.start_span(
            otel_wsgi.get_default_span_name(env),
            kind=trace.SpanKind.SERVER,
            attributes=attributes,
            start_time=start_time,
        )
        activation = self._tracer.use_span(span, end_on_exit=True)
        activation.__enter__()
        env[_ENVIRON_SPAN_KEY] = span
        env[_ENVIRON_ACTIVATION_KEY] = activation

        def _start_response(status, response_headers, *args, **kwargs):
            otel_wsgi.add_response_attributes(span, status, response_headers)
            response = start_response(
                status, response_headers, *args, **kwargs
            )
            activation.__exit__(None, None, None)
            context.detach(token)
            return response

        try:
            return super().__call__(env, _start_response)
        except Exception as exc:
            activation.__exit__(
                type(exc), exc, getattr(exc, "__traceback__", None),
            )
            context.detach(token)
            raise


class _TraceMiddleware:
    # pylint:disable=R0201,W0613

    def __init__(self, tracer=None):
        self.tracer = tracer

    def process_resource(self, req, resp, resource, params):
        span = req.env.get(_ENVIRON_SPAN_KEY)
        if not span:
            return

        resource_name = resource.__class__.__name__
        span.set_attribute("falcon.resource", resource_name)
        span.update_name(
            "{0}.on_{1}".format(resource_name, req.method.lower())
        )

    def process_response(
        self, req, resp, resource, req_succeeded=None
    ):  # pylint:disable=R0201
        span = req.env.get(_ENVIRON_SPAN_KEY)
        if not span:
            return

        status = resp.status
        reason = None
        if resource is None:
            status = "404"
            reason = "NotFound"

        exc_type, exc, _ = sys.exc_info()
        if exc_type and not req_succeeded:
            if "HTTPNotFound" in exc_type.__name__:
                status = "404"
                reason = "NotFound"
            else:
                status = "500"
                reason = "{}: {}".format(exc_type.__name__, exc)

        status = status.split(" ")[0]
        try:
            status_code = int(status)
        except ValueError:
            pass
        finally:
            span.set_attribute("http.status_code", status_code)
            span.set_status(
                Status(
                    canonical_code=http_status_to_canonical_code(status_code),
                    description=reason,
                )
            )
