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
API for propagation of context.

Example::

    import flask
    import requests
    from opentelemetry import propagators


    PROPAGATOR = propagators.get_global_textmap()


    def get_header_from_flask_request(request, key):
        return request.headers.get_all(key)

    def set_header_into_requests_request(request: requests.Request,
                                            key: str, value: str):
        request.headers[key] = value

    def example_route():
        context = PROPAGATOR.extract(
            get_header_from_flask_request,
            flask.request
        )
        request_to_downstream = requests.Request(
            "GET", "http://httpbin.org/get"
        )
        PROPAGATOR.inject(
            set_header_into_requests_request,
            request_to_downstream,
            context=context
        )
        session = requests.Session()
        session.send(request_to_downstream.prepare())


.. _Propagation API Specification:
    https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/api-propagators.md
"""

import typing

from opentelemetry.baggage.propagation import BaggagePropagator
from opentelemetry.context.context import Context
from opentelemetry.propagators import composite
from opentelemetry.trace.propagation import textmap
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
)


def extract(
    get_from_carrier: textmap.Getter[textmap.TextMapPropagatorT],
    carrier: textmap.TextMapPropagatorT,
    context: typing.Optional[Context] = None,
) -> Context:
    """ Uses the configured propagator to extract a Context from the carrier.

    Args:
        get_from_carrier: a function that can retrieve zero
            or more values from the carrier. In the case that
            the value does not exist, return an empty list.
        carrier: and object which contains values that are
            used to construct a Context. This object
            must be paired with an appropriate get_from_carrier
            which understands how to extract a value from it.
        context: an optional Context to use. Defaults to current
            context if not set.
    """
    return get_global_textmap().extract(get_from_carrier, carrier, context)


def inject(
    set_in_carrier: textmap.Setter[textmap.TextMapPropagatorT],
    carrier: textmap.TextMapPropagatorT,
    context: typing.Optional[Context] = None,
) -> None:
    """ Uses the configured propagator to inject a Context into the carrier.

    Args:
        set_in_carrier: A setter function that can set values
            on the carrier.
        carrier: An object that contains a representation of HTTP
            headers. Should be paired with set_in_carrier, which
            should know how to set header values on the carrier.
        context: an optional Context to use. Defaults to current
            context if not set.
    """
    get_global_textmap().inject(set_in_carrier, carrier, context)


_HTTP_TEXT_FORMAT = composite.CompositeHTTPPropagator(
    [TraceContextTextMapPropagator(), BaggagePropagator()],
)  # type: textmap.TextMapPropagator


def get_global_textmap() -> textmap.TextMapPropagator:
    return _HTTP_TEXT_FORMAT


def set_global_textmap(http_text_format: textmap.TextMapPropagator,) -> None:
    global _HTTP_TEXT_FORMAT  # pylint:disable=global-statement
    _HTTP_TEXT_FORMAT = http_text_format
