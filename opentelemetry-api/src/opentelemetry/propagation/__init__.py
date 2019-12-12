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

import typing

import opentelemetry.context.propagation.httptextformat as httptextformat
import opentelemetry.trace as trace
from opentelemetry.context.propagation.tracecontexthttptextformat import (
    TraceContextHTTPExtractor,
    TraceContextHTTPInjector,
)
from opentelemetry.context import BaseRuntimeContext

_T = typing.TypeVar("_T")


def extract(
    context: BaseRuntimeContext,
    get_from_carrier: httptextformat.Getter[_T],
    carrier: _T,
) -> typing.Optional[BaseRuntimeContext]:
    """Load the parent SpanContext from values in the carrier.

    Using the specified HTTPExtractor, the propagator will
    extract a SpanContext from the carrier. If one is found,
    it will be set as the parent context of the current span.

    Args:
        get_from_carrier: a function that can retrieve zero
            or more values from the carrier. In the case that
            the value does not exist, return an empty list.
        carrier: and object which contains values that are
            used to construct a SpanContext. This object
            must be paired with an appropriate get_from_carrier
            which understands how to extract a value from it.
    """
    for extractor in get_http_extractors():
        return extractor.extract(context, get_from_carrier, carrier)
    return None


def inject(
    context: BaseRuntimeContext,
    set_in_carrier: httptextformat.Setter[_T],
    carrier: _T,
) -> None:
    """Inject values from the current context into the carrier.

    inject enables the propagation of values into HTTP clients or
    other objects which perform an HTTP request. Implementations
    should use the set_in_carrier method to set values on the
    carrier.

    Args:
        set_in_carrier: A setter function that can set values
            on the carrier.
        carrier: An object that contains a representation of HTTP
            headers. Should be paired with set_in_carrier, which
            should know how to set header values on the carrier.
    """
    for injector in get_http_injectors():
        injector.inject(context, set_in_carrier, carrier)


_HTTP_TEXT_INJECTORS = [
    TraceContextHTTPInjector
]  # typing.List[httptextformat.HTTPInjector]

_HTTP_TEXT_EXTRACTORS = [
    TraceContextHTTPExtractor
]  # typing.List[httptextformat.HTTPExtractor]


def set_http_extractors(
    extractor_list: typing.List[httptextformat.HTTPExtractor],
) -> None:
    global _HTTP_TEXT_EXTRACTORS  # pylint:disable=global-statement
    _HTTP_TEXT_EXTRACTORS = extractor_list


def set_http_injectors(
    injector_list: typing.List[httptextformat.HTTPInjector],
) -> None:
    global _HTTP_TEXT_INJECTORS  # pylint:disable=global-statement
    _HTTP_TEXT_INJECTORS = injector_list


def get_http_extractors() -> typing.List[httptextformat.HTTPExtractor]:
    return _HTTP_TEXT_EXTRACTORS


def get_http_injectors() -> typing.List[httptextformat.HTTPInjector]:
    return _HTTP_TEXT_INJECTORS
