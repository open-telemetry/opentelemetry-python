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

from logging import getLogger

from opentelemetry.configuration import Configuration
from opentelemetry.context import attach, detach
from opentelemetry.ext.django.version import __version__
from opentelemetry.ext.wsgi import (
    add_response_attributes,
    collect_request_attributes,
    get_header_from_environ,
)
from opentelemetry.propagators import extract
from opentelemetry.trace import SpanKind, get_tracer
from opentelemetry.util import disable_trace

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object

_logger = getLogger(__name__)


class _DjangoMiddleware(MiddlewareMixin):
    """Django Middleware for OpenTelemetry
    """

    _environ_activation_key = (
        "opentelemetry-instrumentor-django.activation_key"
    )
    _environ_token = "opentelemetry-instrumentor-django.token"
    _environ_span_key = "opentelemetry-instrumentor-django.span_key"

    _excluded_hosts = Configuration().DJANGO_EXCLUDED_HOSTS or []
    _excluded_paths = Configuration().DJANGO_EXCLUDED_PATHS or []
    if _excluded_hosts:
        _excluded_hosts = str.split(_excluded_hosts, ",")
    if _excluded_paths:
        _excluded_paths = str.split(_excluded_paths, ",")
    def process_view(
        self, request, view_func, view_args, view_kwargs
    ):  # pylint: disable=unused-argument
        # request.META is a dictionary containing all available HTTP headers
        # Read more about request.META here:
        # https://docs.djangoproject.com/en/3.0/ref/request-response/#django.http.HttpRequest.META

        # environ = {
        #     key.lower().replace('_', '-').replace("http-", "", 1): value
        #     for key, value in request.META.items()
        # }
        if disable_trace(
            request.build_absolute_uri("?"),
            self._excluded_hosts,
            self._excluded_paths
        ):
            return

        environ = request.META

        token = attach(extract(get_header_from_environ, environ))

        tracer = get_tracer(__name__, __version__)

        attributes = collect_request_attributes(environ)

        span = tracer.start_span(
            view_func.__name__,
            kind=SpanKind.SERVER,
            attributes=attributes,
            start_time=environ.get(
                "opentelemetry-instrumentor-django.starttime_key"
            ),
        )

        activation = tracer.use_span(span, end_on_exit=True)
        activation.__enter__()

        request.META[self._environ_activation_key] = activation
        request.META[self._environ_span_key] = span
        request.META[self._environ_token] = token

    def process_exception(self, request, exception):
        # Django can call this method and process_response later. In order
        # to avoid __exit__ and detach from being called twice then, the
        # respective keys are being removed here.
        if disable_trace(
            request.build_absolute_uri("?"),
            self._excluded_hosts,
            self._excluded_paths
        ):
            return

        if self._environ_activation_key in request.META.keys():
            request.META[self._environ_activation_key].__exit__(
                type(exception),
                exception,
                getattr(exception, "__traceback__", None),
            )
            request.META.pop(self._environ_activation_key)

            detach(request.environ[self._environ_token])
            request.META.pop(self._environ_token, None)

    def process_response(self, request, response):
        if disable_trace(
            request.build_absolute_uri("?"),
            self._excluded_hosts,
            self._excluded_paths
        ):
            return response

        if (
            self._environ_activation_key in request.META.keys()
            and self._environ_span_key in request.META.keys()
        ):
            add_response_attributes(
                request.META[self._environ_span_key],
                "{} {}".format(response.status_code, response.reason_phrase),
                response,
            )
            request.META.pop(self._environ_span_key)

            request.META[self._environ_activation_key].__exit__(
                None, None, None
            )
            request.META.pop(self._environ_activation_key)

        if self._environ_token in request.META.keys():
            detach(request.environ.get(self._environ_token))
            request.META.pop(self._environ_token)

        return response
