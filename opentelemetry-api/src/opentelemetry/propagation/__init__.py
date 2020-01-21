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

import abc
import typing

import opentelemetry.trace as trace
from opentelemetry.context import Context, current

ContextT = typing.TypeVar("ContextT")

Setter = typing.Callable[[ContextT, str, str], None]
Getter = typing.Callable[[ContextT, str], typing.List[str]]


class Extractor(abc.ABC):
    """API for propagation of span context via headers.

    TODO: update docs to reflect split into extractor/injector

    This class provides an interface that enables extracting and injecting
    span context into headers of HTTP requests. HTTP frameworks and clients
    can integrate with HTTPTextFormat by providing the object containing the
    headers, and a getter and setter function for the extraction and
    injection of values, respectively.

    Example::

        import flask
        import requests
        from opentelemetry.context.propagation import Extractor

        PROPAGATOR = HTTPTextFormat()



        def get_header_from_flask_request(request, key):
            return request.headers.get_all(key)

        def set_header_into_requests_request(request: requests.Request,
                                             key: str, value: str):
            request.headers[key] = value

        def example_route():
            span_context = PROPAGATOR.extract(
                get_header_from_flask_request,
                flask.request
            )
            request_to_downstream = requests.Request(
                "GET", "http://httpbin.org/get"
            )
            PROPAGATOR.inject(
                span_context,
                set_header_into_requests_request,
                request_to_downstream
            )
            session = requests.Session()
            session.send(request_to_downstream.prepare())


    .. _Propagation API Specification:
       https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/api-propagators.md
    """

    @classmethod
    @abc.abstractmethod
    def extract(
        cls,
        carrier: ContextT,
        context: typing.Optional[Context] = None,
        get_from_carrier: typing.Optional[Getter[ContextT]] = None,
    ) -> Context:
        """Create a Context from values in the carrier.

        The extract function should retrieve values from the carrier
        object using get_from_carrier, use values to populate a
        Context value and return it.

        Args:
            carrier: and object which contains values that are
                used to construct a Context. This object
                must be paired with an appropriate get_from_carrier
                which understands how to extract a value from it.
            context: The Context to read values from.
            get_from_carrier: a function that can retrieve zero
                or more values from the carrier. In the case that
                the value does not exist, return an empty list.
        Returns:
            A Context with configuration found in the carrier.
        """


class Injector(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def inject(
        cls,
        carrier: ContextT,
        context: typing.Optional[Context] = None,
        set_in_carrier: typing.Optional[Setter[ContextT]] = None,
    ) -> None:
        """Inject values from a Context into a carrier.

        inject enables the propagation of values into HTTP clients or
        other objects which perform an HTTP request. Implementations
        should use the set_in_carrier method to set values on the
        carrier.

        Args:
            carrier: An object that a place to define HTTP headers.
                Should be paired with set_in_carrier, which should
                know how to set header values on the carrier.
            context: The Context to read values from.
            set_in_carrier: A setter function that can set values
                on the carrier.
        """


class DefaultExtractor(Extractor):
    """The default Extractor that is used when no Extractor implementation is configured.

    All operations are no-ops.
    """

    @classmethod
    def extract(
        cls,
        carrier: ContextT,
        context: typing.Optional[Context] = None,
        get_from_carrier: typing.Optional[Getter[ContextT]] = None,
    ) -> Context:
        if context:
            return context
        return current()


class DefaultInjector(Injector):
    """The default Injector that is used when no Injector implementation is configured.

    All operations are no-ops.
    """

    @classmethod
    def inject(
        cls,
        carrier: ContextT,
        context: typing.Optional[Context] = None,
        set_in_carrier: typing.Optional[Setter[ContextT]] = None,
    ) -> None:
        return None


def extract(
    carrier: ContextT,
    context: typing.Optional[Context] = None,
    extractors: typing.Optional[typing.List[Extractor]] = None,
    get_from_carrier: typing.Optional[Getter[ContextT]] = None,
) -> typing.Optional[Context]:
    """Load the parent SpanContext from values in the carrier.

    Using the specified Extractor, the propagator will
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
    if context is None:
        context = current()
    if extractors is None:
        extractors = get_http_extractors()

    for extractor in extractors:
        # TODO: improve this
        if get_from_carrier:
            return extractor.extract(
                context=context,
                carrier=carrier,
                get_from_carrier=get_from_carrier,
            )
        return extractor.extract(context=context, carrier=carrier)

    return None


def inject(
    carrier: ContextT,
    injectors: typing.Optional[typing.List[Injector]] = None,
    context: typing.Optional[Context] = None,
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
    if context is None:
        context = current()
    if injectors is None:
        injectors = get_http_injectors()

    for injector in injectors:
        injector.inject(context=context, carrier=carrier)


_HTTP_TEXT_INJECTORS = [
    DefaultInjector
]  # typing.List[httptextformat.Injector]

_HTTP_TEXT_EXTRACTORS = [
    DefaultExtractor
]  # typing.List[httptextformat.Extractor]


def set_http_extractors(extractor_list: typing.List[Extractor],) -> None:
    """
    To update the global extractor, the Propagation API provides a
    function which takes an extractor.
    """
    global _HTTP_TEXT_EXTRACTORS  # pylint:disable=global-statement
    _HTTP_TEXT_EXTRACTORS = extractor_list  # type: ignore


def set_http_injectors(injector_list: typing.List[Injector],) -> None:
    """
    To update the global injector, the Propagation API provides a
    function which takes an injector.
    """
    global _HTTP_TEXT_INJECTORS  # pylint:disable=global-statement
    _HTTP_TEXT_INJECTORS = injector_list  # type: ignore


def get_http_extractors() -> typing.List[Extractor]:
    """
    To access the global extractor, the Propagation API provides
    a function which returns an extractor.
    """
    return _HTTP_TEXT_EXTRACTORS  # type: ignore


def get_http_injectors() -> typing.List[Injector]:
    """
    To access the global injector, the Propagation API provides a
    function which returns an injector.
    """
    return _HTTP_TEXT_INJECTORS  # type: ignore


def get_as_list(
    dict_object: typing.Dict[str, str], key: str
) -> typing.List[str]:
    value = dict_object.get(key)
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def set_in_dict(
    dict_object: typing.Dict[str, str], key: str, value: str
) -> None:
    dict_object[key] = value
