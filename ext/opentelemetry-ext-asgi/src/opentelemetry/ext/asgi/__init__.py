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
The opentelemetry-ext-asgi package provides an ASGI middleware that can be used
on any ASGI framework (such as Django-channels / Quart) to track requests
timing through OpenTelemetry.
"""

import operator
import typing
from functools import wraps

from asgiref.compatibility import guarantee_single_callable

from opentelemetry import context, propagators, trace
from opentelemetry.ext.asgi.version import __version__  # noqa
from opentelemetry.trace.status import Status, StatusCanonicalCode


def get_header_from_scope(scope: dict, header_name: str) -> typing.List[str]:
    """Retrieve a HTTP header value from the ASGI scope.

    Returns:
        A list with a single string with the header value if it exists, else an empty list.
    """
    headers = scope.get("headers")
    return [
        value.decode("utf8")
        for (key, value) in headers
        if key.decode("utf8") == header_name
    ]


def http_status_to_canonical_code(code: int, allow_redirect: bool = True):
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


def collect_request_attributes(scope):
    """Collects HTTP request attributes from the ASGI scope and returns a
    dictionary to be used as span creation attributes."""
    server = scope.get("server") or ["0.0.0.0", 80]
    port = server[1]
    server_host = server[0] + (":" + str(port) if port != 80 else "")
    http_url = (
        scope.get("scheme") + "://" + server_host + scope.get("path", "")
        if scope.get("scheme") and server_host and scope.get("path")
        else None
    )
    if scope.get("query_string") and http_url:
        http_url = http_url + ("?" + scope.get("query_string").decode("utf8"))

    result = {
        "component": scope.get("type"),
        "http.scheme": scope.get("scheme"),
        "http.host": server_host,
        "host.port": port,
        "http.flavor": scope.get("http_version"),
        "http.target": scope.get("path"),
        "http.url": http_url,
    }
    http_method = scope.get("method")
    if http_method:
        result["http.method"] = http_method
    http_host_value = ",".join(get_header_from_scope(scope, "host"))
    if http_host_value:
        result["http.server_name"] = http_host_value
    http_user_agent = get_header_from_scope(scope, "user-agent")
    if len(http_user_agent) > 0:
        result["http.user_agent"] = http_user_agent[0]

    if "client" in scope and scope["client"] is not None:
        result["net.peer.ip"] = scope.get("client")[0]
        result["net.peer.port"] = scope.get("client")[1]

    # remove None values
    result = {k: v for k, v in result.items() if v is not None}

    return result


def set_status_code(span, status_code):
    """Adds HTTP response attributes to span using the status_code argument."""
    try:
        status_code = int(status_code)
    except ValueError:
        span.set_status(
            Status(
                StatusCanonicalCode.UNKNOWN,
                "Non-integer HTTP status: " + repr(status_code),
            )
        )
    else:
        span.set_attribute("http.status_code", status_code)
        span.set_status(Status(http_status_to_canonical_code(status_code)))


def get_default_span_name(scope):
    """Default implementation for name_callback"""
    method_or_path = scope.get("method") or scope.get("path")

    return method_or_path


class OpenTelemetryMiddleware:
    """The ASGI application middleware.

    This class is an ASGI middleware that starts and annotates spans for any
    requests it is invoked with.

    Args:
        app: The ASGI application callable to forward requests to.
        name_callback: Callback which calculates a generic span name for an
                       incoming HTTP request based on the ASGI scope.
                       Optional: Defaults to get_default_span_name.
    """

    def __init__(self, app, name_callback=None):
        self.app = guarantee_single_callable(app)
        self.tracer = trace.get_tracer(__name__, __version__)
        self.name_callback = name_callback or get_default_span_name

    async def __call__(self, scope, receive, send):
        """The ASGI application

        Args:
            scope: A ASGI environment.
            receive: An awaitable callable yielding dictionaries
            send: An awaitable callable taking a single dictionary as argument.
        """
        if scope.get("type") not in ("http", "websocket"):
            return await self.app(scope, receive, send)

        token = context.attach(
            propagators.extract(get_header_from_scope, scope)
        )
        span_name = self.name_callback(scope)

        try:
            with self.tracer.start_as_current_span(
                span_name + " asgi",
                kind=trace.SpanKind.SERVER,
                attributes=collect_request_attributes(scope),
            ):

                @wraps(receive)
                async def wrapped_receive():
                    with self.tracer.start_as_current_span(
                        span_name + " asgi." + scope["type"] + ".receive"
                    ) as receive_span:
                        payload = await receive()
                        if payload["type"] == "websocket.receive":
                            set_status_code(receive_span, 200)
                        receive_span.set_attribute("type", payload["type"])
                    return payload

                @wraps(send)
                async def wrapped_send(payload):
                    with self.tracer.start_as_current_span(
                        span_name + " asgi." + scope["type"] + ".send"
                    ) as send_span:
                        if payload["type"] == "http.response.start":
                            status_code = payload["status"]
                            set_status_code(send_span, status_code)
                        elif payload["type"] == "websocket.send":
                            set_status_code(send_span, 200)
                        send_span.set_attribute("type", payload["type"])
                        await send(payload)

                await self.app(scope, wrapped_receive, wrapped_send)
        finally:
            context.detach(token)
