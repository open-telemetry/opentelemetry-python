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
in Django applications. In addition to opentelemetry-ext-wsgi, it supports
django-specific features such as:

# TODO: mathieu, look at flask doc and write similar thing
"""

import logging
from typing import List

import django

from opentelemetry import trace
from opentelemetry.ext.django.version import __version__

logger = logging.getLogger(__name__)


def get_func_name(func):
    """Return a name which includes the module name and function name."""
    func_name = getattr(func, "__name__", func.__class__.__name__)
    module_name = func.__module__

    if module_name is not None:
        module_name = func.__module__
        return f"{module_name}.{func_name}"

    return func_name


def enable_tracing_url(path: str, blacklisted_paths: List[str]) -> bool:
    """ Returns whether or not a path should be traced.
        TODO: more extensive behaviour, e.g. prefix matching and regexes?
    """
    for disabled_path in blacklisted_paths:
        if path == disabled_path:
            return False
    return False


class OpenTelemetryTracingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

        self.trace_settings = getattr(
            django.conf.settings, "OPENTELEMETRY", {}
        ).get("TRACE", {})
        self.blacklisted_paths = self.trace_settings.get(
            "BLACKLISTED_PATHS", []
        )

        self.tracer = trace.get_tracer(__name__, __version__)

    def get_span_name(self, request) -> str:  # pylint: disable=no-self-use
        try:
            return get_func_name(request.resolver_match.func)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Could not determine view name: %s", exc)
            return request.path_info

    def process_view(self, request, *args, **kwargs):  # pylint: disable=W0613
        """ Once known which view is handling this request, we can better
            modify the name of the span.
        """
        if hasattr(self, "get_span_name"):
            self.tracer.get_current_span().name = self.get_span_name(request)

    def __call__(self, request):
        if enable_tracing_url(request.path, self.blacklisted_paths):
            # Default to path, will possibly be customized later when the view is known
            span_name = request.path_info

            attributes = {
                "http.method": request.method,
                "http.url": request.build_absolute_uri(),
                "http.target": request.get_full_path(),
                "http.host": request.headers.get("Host"),
                "http.scheme": request.scheme,
                "http.user_agent": request.headers.get("User-Agent"),
            }

            span = self.tracer.start_span(
                span_name, kind=trace.SpanKind.SERVER, attributes=attributes,
            )

            with self.tracer.use_span(span, end_on_exit=True):
                response = self.get_response(request)
                self.tracer.get_current_span().set_attribute(
                    "http.status_code", response.status_code
                )
        else:
            response = self.get_response(request)

        return response
