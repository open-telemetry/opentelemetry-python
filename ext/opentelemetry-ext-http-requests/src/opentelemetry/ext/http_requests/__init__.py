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
`requests <https://requests.kennethreitz.org/en/master/>`_ library.

Usage
-----

.. code-block:: python

    import requests
    import opentelemetry.ext.http_requests
    from opentelemetry.trace import TracerProvider

    opentelemetry.ext.http_requests.enable(TracerProvider())
    response = requests.get(url='https://www.example.org/')

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
from urllib.parse import urlparse

from requests.sessions import Session

from opentelemetry import context, propagators
from opentelemetry.ext.http_requests.version import __version__
from opentelemetry.trace import SpanKind


# NOTE: Currently we force passing a tracer. But in turn, this forces the user
# to configure a SDK before enabling this integration. In turn, this means that
# if the SDK/tracer is already using `requests` they may, in theory, bypass our
# instrumentation when using `import from`, etc. (currently we only instrument
# a instance method so the probability for that is very low).
def enable(tracer_provider):
    """Enables tracing of all requests calls that go through
      :code:`requests.session.Session.request` (this includes
      :code:`requests.get`, etc.)."""

    # Since
    # https://github.com/psf/requests/commit/d72d1162142d1bf8b1b5711c664fbbd674f349d1
    # (v0.7.0, Oct 23, 2011), get, post, etc are implemented via request which
    # again, is implemented via Session.request (`Session` was named `session`
    # before v1.0.0, Dec 17, 2012, see
    # https://github.com/psf/requests/commit/4e5c4a6ab7bb0195dececdd19bb8505b872fe120)

    # Guard against double instrumentation
    disable()

    tracer = tracer_provider.get_tracer(__name__, __version__)

    wrapped = Session.request

    @functools.wraps(wrapped)
    def instrumented_request(self, method, url, *args, **kwargs):
        if context.get_value("suppress_instrumentation"):
            return wrapped(self, method, url, *args, **kwargs)

        # See
        # https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/data-semantic-conventions.md#http-client
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

            # TODO: Propagate the trace context via headers once we have a way
            # to access propagators.

            headers = kwargs.setdefault("headers", {})
            propagators.inject(type(headers).__setitem__, headers)
            result = wrapped(self, method, url, *args, **kwargs)  # *** PROCEED

            span.set_attribute("http.status_code", result.status_code)
            span.set_attribute("http.status_text", result.reason)

            return result

        # TODO: How to handle exceptions? Should we create events for them? Set
        # certain attributes?

    instrumented_request.opentelemetry_ext_requests_applied = True

    Session.request = instrumented_request

    # TODO: We should also instrument requests.sessions.Session.send
    # but to avoid doubled spans, we would need some context-local
    # state (i.e., only create a Span if the current context's URL is
    # different, then push the current URL, pop it afterwards)


def disable():
    """Disables instrumentation of :code:`requests` through this module.

    Note that this only works if no other module also patches requests."""

    if getattr(Session.request, "opentelemetry_ext_requests_applied", False):
        original = Session.request.__wrapped__  # pylint:disable=no-member
        Session.request = original
