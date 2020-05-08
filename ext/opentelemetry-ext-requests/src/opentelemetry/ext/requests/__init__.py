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
This library allows tracing HTTP requests made by the
`requests <https://requests.readthedocs.io/en/master/>`_ library.

Usage
-----

.. code-block:: python

    import requests
    import opentelemetry.ext.requests

    # You can optionally pass a custom TracerProvider to RequestInstrumentor.instrument()
    opentelemetry.ext.requests.RequestInstrumentor.instrument()
    response = requests.get(url="https://www.example.org/")

Limitations
-----------

Note that calls that do not use the higher-level APIs but use
:code:`requests.sessions.Session.send` (or an alias thereof) directly, are
currently not traced. If you find any other way to trigger an untraced HTTP
request, please report it via a GitHub issue with :code:`[requests: untraced
API]` in the title.

API
---
"""

import functools
import types
from urllib.parse import urlparse

from requests.sessions import Session

from opentelemetry import context, propagators, trace
from opentelemetry.auto_instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.ext.requests.version import __version__
from opentelemetry.trace import SpanKind, get_tracer
from opentelemetry.trace.status import Status, StatusCanonicalCode


# pylint: disable=unused-argument
def _instrument(tracer_provider=None):
    """Enables tracing of all requests calls that go through
      :code:`requests.session.Session.request` (this includes
      :code:`requests.get`, etc.)."""

    # Since
    # https://github.com/psf/requests/commit/d72d1162142d1bf8b1b5711c664fbbd674f349d1
    # (v0.7.0, Oct 23, 2011), get, post, etc are implemented via request which
    # again, is implemented via Session.request (`Session` was named `session`
    # before v1.0.0, Dec 17, 2012, see
    # https://github.com/psf/requests/commit/4e5c4a6ab7bb0195dececdd19bb8505b872fe120)

    wrapped = Session.request

    tracer = trace.get_tracer(__name__, __version__, tracer_provider)

    @functools.wraps(wrapped)
    def instrumented_request(self, method, url, *args, **kwargs):
        if context.get_value("suppress_instrumentation"):
            return wrapped(self, method, url, *args, **kwargs)

        # See
        # https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/trace/semantic_conventions/http.md#http-client
        try:
            parsed_url = urlparse(url)
        except ValueError as exc:  # Invalid URL
            path = "<Unparsable URL: {}>".format(exc)
        else:
            if parsed_url is None:
                path = "<URL parses to None>"
            path = parsed_url.path

        with tracer.start_as_current_span(path, kind=SpanKind.CLIENT) as span:
            span.set_attribute("component", "http")
            span.set_attribute("http.method", method.upper())
            span.set_attribute("http.url", url)

            headers = kwargs.setdefault("headers", {})
            propagators.inject(type(headers).__setitem__, headers)
            result = wrapped(self, method, url, *args, **kwargs)  # *** PROCEED

            span.set_attribute("http.status_code", result.status_code)
            span.set_attribute("http.status_text", result.reason)
            span.set_status(
                Status(_http_status_to_canonical_code(result.status_code))
            )

            return result

    instrumented_request.opentelemetry_ext_requests_applied = True

    Session.request = instrumented_request

    # TODO: We should also instrument requests.sessions.Session.send
    # but to avoid doubled spans, we would need some context-local
    # state (i.e., only create a Span if the current context's URL is
    # different, then push the current URL, pop it afterwards)


def _uninstrument():
    # pylint: disable=global-statement
    """Disables instrumentation of :code:`requests` through this module.

    Note that this only works if no other module also patches requests."""
    if getattr(Session.request, "opentelemetry_ext_requests_applied", False):
        original = Session.request.__wrapped__  # pylint:disable=no-member
        Session.request = original


def _http_status_to_canonical_code(code: int, allow_redirect: bool = True):
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


class RequestsInstrumentor(BaseInstrumentor):
    def _instrument(self, **kwargs):
        _instrument(tracer_provider=kwargs.get("tracer_provider"))

    def _uninstrument(self, **kwargs):
        _uninstrument()

    @staticmethod
    def uninstrument_session(session):
        """Disables instrumentation on the session object."""
        if getattr(
            session.request, "opentelemetry_ext_requests_applied", False
        ):
            original = session.request.__wrapped__  # pylint:disable=no-member
            session.request = types.MethodType(original, session)
