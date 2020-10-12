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

import time
from logging import getLogger

from django.conf import settings

from opentelemetry.configuration import Configuration
from opentelemetry.context import attach, detach
from opentelemetry.instrumentation.django.version import __version__
from opentelemetry.instrumentation.utils import extract_attributes_from_object
from opentelemetry.instrumentation.wsgi import (
    add_response_attributes,
    collect_request_attributes,
    get_header_from_environ,
)
from opentelemetry.propagators import extract
from opentelemetry.trace import SpanKind, get_tracer
from opentelemetry.util import ExcludeList

try:
    from django.core.urlresolvers import (  # pylint: disable=no-name-in-module
        resolve,
        Resolver404,
    )
except ImportError:
    from django.urls import resolve, Resolver404

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object

_logger = getLogger(__name__)


class _DjangoMiddleware(MiddlewareMixin):
    """Django Middleware for OpenTelemetry"""

    _environ_activation_key = (
        "opentelemetry-instrumentor-django.activation_key"
    )
    _environ_token = "opentelemetry-instrumentor-django.token"
    _environ_span_key = "opentelemetry-instrumentor-django.span_key"

    _excluded_urls = Configuration().DJANGO_EXCLUDED_URLS or []
    if _excluded_urls:
        _excluded_urls = ExcludeList(str.split(_excluded_urls, ","))
    else:
        _excluded_urls = ExcludeList(_excluded_urls)

    _traced_request_attrs = [
        attr.strip()
        for attr in (Configuration().DJANGO_TRACED_REQUEST_ATTRS or "").split(
            ","
        )
    ]

    @staticmethod
    def _get_span_name(request):
        try:
            if getattr(request, "resolver_match"):
                match = request.resolver_match
            else:
                match = resolve(request.get_full_path())

            if hasattr(match, "route"):
                return match.route

            # Instead of using `view_name`, better to use `_func_name` as some applications can use similar
            # view names in different modules
            if hasattr(match, "_func_name"):
                return match._func_name  # pylint: disable=protected-access

            # Fallback for safety as `_func_name` private field
            return match.view_name

        except Resolver404:
            return "HTTP {}".format(request.method)

    @staticmethod
    def _get_metric_labels_from_attributes(attributes):
        labels = {}
        labels["http.method"] = attributes.get("http.method", "")
        if attributes.get("http.url"):
            labels["http.url"] = attributes.get("http.url")
        elif attributes.get("http.scheme"):
            labels["http.scheme"] = attributes.get("http.scheme")
            if attributes.get("http.target"):
                labels["http.target"] = attributes.get("http.target")
                if attributes.get("http.host"):
                    labels["http.host"] = attributes.get("http.host")
                elif attributes.get("net.host.port"):
                    labels["net.host.port"] = attributes.get("net.host.port")
                    if attributes.get("http.server_name"):
                        labels["http.server_name"] = attributes.get(
                            "http.server_name"
                        )
                    elif attributes.get("http.host.name"):
                        labels["http.host.name"] = attributes.get(
                            "http.host.name"
                        )
        if attributes.get("http.flavor"):
            labels["http.flavor"] = attributes.get("http.flavor")
        return labels

    def process_request(self, request):
        # request.META is a dictionary containing all available HTTP headers
        # Read more about request.META here:
        # https://docs.djangoproject.com/en/3.0/ref/request-response/#django.http.HttpRequest.META

        if self._excluded_urls.url_disabled(request.build_absolute_uri("?")):
            return

        request.start_time = time.time()

        environ = request.META

        token = attach(extract(get_header_from_environ, environ))

        tracer = get_tracer(__name__, __version__)

        span = tracer.start_span(
            self._get_span_name(request),
            kind=SpanKind.SERVER,
            start_time=environ.get(
                "opentelemetry-instrumentor-django.starttime_key"
            ),
        )

        attributes = collect_request_attributes(environ)
        request.labels = self._get_metric_labels_from_attributes(attributes)

        if span.is_recording():
            attributes = extract_attributes_from_object(
                request, self._traced_request_attrs, attributes
            )
            for key, value in attributes.items():
                span.set_attribute(key, value)

        activation = tracer.use_span(span, end_on_exit=True)
        activation.__enter__()

        request.META[self._environ_activation_key] = activation
        request.META[self._environ_span_key] = span
        request.META[self._environ_token] = token

    def process_exception(self, request, exception):
        # Django can call this method and process_response later. In order
        # to avoid __exit__ and detach from being called twice then, the
        # respective keys are being removed here.
        if self._excluded_urls.url_disabled(request.build_absolute_uri("?")):
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
        if self._excluded_urls.url_disabled(request.build_absolute_uri("?")):
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
            request.labels["http.status_code"] = str(response.status_code)
            request.META.pop(self._environ_span_key)

            request.META[self._environ_activation_key].__exit__(
                None, None, None
            )
            request.META.pop(self._environ_activation_key)

        if self._environ_token in request.META.keys():
            detach(request.environ.get(self._environ_token))
            request.META.pop(self._environ_token)

        try:
            metric_recorder = getattr(settings, "OTEL_METRIC_RECORDER", None)
            if metric_recorder:
                metric_recorder.record_server_duration_range(
                    request.start_time, time.time(), request.labels
                )
        except Exception as ex:  # pylint: disable=W0703
            _logger.warning("Error recording duration metrics: {}", ex)

        return response
