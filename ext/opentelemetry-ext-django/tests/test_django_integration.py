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

import logging
import sys
import unittest
from unittest import mock

from django.conf import settings as django_settings
from django.conf.urls import url
from django.http import HttpResponse
from django.test import Client, RequestFactory
from django.test.utils import setup_test_environment, teardown_test_environment
from django.urls.resolvers import ResolverMatch
from django.views import View

from opentelemetry import trace as trace_api
from opentelemetry.ext.django import OpenTelemetryTracingMiddleware
from opentelemetry.ext.testutil.wsgitestutil import WsgiTestBase

logger = logging.getLogger(__name__)


def get_func_name(func):
    """Return a name which includes the module name and function name."""
    func_name = getattr(func, "__name__", func.__class__.__name__)
    module_name = func.__module__

    if module_name is not None:
        module_name = func.__module__
        return f"{module_name}.{func_name}"

    return func_name


class MockViewError(View):
    def get(self, *args, **kwargs):  # pylint: disable=unused-argument
        return HttpResponse(
            f"request: {self.request}, args: {args}, kwargs: {kwargs}",
            status=500,
        )

    def post(self, *args, **kwargs):  # pylint: disable=unused-argument
        return HttpResponse(
            f"request: {self.request}, args: {args}, kwargs: {kwargs}",
            status=500,
        )


class MockViewOk(View):
    def get(self, *args, **kwargs):  # pylint: disable=unused-argument
        return HttpResponse(
            f"request: {self.request}, args: {args}, kwargs: {kwargs}",
            status=200,
        )

    def post(self, *args, **kwargs):  # pylint: disable=unused-argument
        return HttpResponse(
            f"request: {self.request}, args: {args}, kwargs: {kwargs}",
            status=200,
        )


class CustomMiddleware(OpenTelemetryTracingMiddleware):
    """ Use the name of the view as the span name instead of the request path """

    def get_span_name(self, request) -> str:  # pylint: disable=no-self-use
        try:
            return get_func_name(request.resolver_match.func)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Could not determine view name: %s", exc)
            return request.path_info


urlpatterns = [
    url(r"^ok", MockViewOk.as_view()),
    url(r"^error", MockViewError.as_view()),
]


class TestDjangoIntegration(WsgiTestBase):
    def setUp(self):
        super().setUp()

        if not django_settings.configured:
            django_settings.configure(ROOT_URLCONF=sys.modules[__name__])
        setup_test_environment()

    def tearDown(self):
        super().tearDown()
        teardown_test_environment()

    def test_constructor_default(self):  # pylint: disable=no-self-use
        middleware_obj = OpenTelemetryTracingMiddleware(mock.Mock())

        assert middleware_obj.blacklisted_paths == []

    def test_constructor_blacklist_settings(
        self,
    ):  # pylint: disable=no-self-use
        settings = type("Test", (object,), {})
        settings.OPENTELEMETRY = {
            "TRACE": {"BLACKLISTED_PATHS": ["/_ah/health/"]}
        }
        patch_settings = mock.patch("django.conf.settings", settings)

        with patch_settings:
            middleware_obj = OpenTelemetryTracingMiddleware(mock.Mock())

        assert middleware_obj.blacklisted_paths == ["/_ah/health/"]

    def test_span_attributes_get_200(self):
        django_request = RequestFactory().get("/hello_endpoint/", **{})
        django_request.resolver_match = ResolverMatch(
            MockViewOk.as_view(), None, None
        )

        middleware_obj = OpenTelemetryTracingMiddleware(MockViewOk.as_view())

        expected_attributes = {
            "http.method": "GET",
            "http.url": "http://testserver/hello_endpoint/",
            "http.target": "/hello_endpoint/",
            "http.host": None,
            "http.scheme": "http",
            "http.user_agent": None,
            "http.status_code": 200,
        }

        middleware_obj(django_request)

        span_list = self.memory_exporter.get_finished_spans()

        assert len(span_list) == 1
        assert span_list[0].name == "/hello_endpoint/"
        assert span_list[0].kind == trace_api.SpanKind.SERVER
        assert span_list[0].attributes == expected_attributes

    def test_span_attributes_post_200(self):
        django_request = RequestFactory().post("/hello_endpoint/", **{})
        django_request.resolver_match = ResolverMatch(
            MockViewOk.as_view(), None, None
        )

        middleware_obj = OpenTelemetryTracingMiddleware(MockViewOk.as_view())

        expected_attributes = {
            "http.method": "POST",
            "http.url": "http://testserver/hello_endpoint/",
            "http.target": "/hello_endpoint/",
            "http.host": None,
            "http.scheme": "http",
            "http.user_agent": None,
            "http.status_code": 200,
        }

        middleware_obj(django_request)

        span_list = self.memory_exporter.get_finished_spans()

        assert len(span_list) == 1
        assert span_list[0].name == "/hello_endpoint/"
        assert span_list[0].kind == trace_api.SpanKind.SERVER
        assert span_list[0].attributes == expected_attributes

    def test_span_attributes_get_500(self):
        django_request = RequestFactory().get("/error/", **{})
        django_request.resolver_match = ResolverMatch(
            MockViewError.as_view(), None, None
        )

        middleware_obj = OpenTelemetryTracingMiddleware(
            MockViewError.as_view()
        )

        expected_attributes = {
            "http.method": "GET",
            "http.url": "http://testserver/error/",
            "http.target": "/error/",
            "http.host": None,
            "http.scheme": "http",
            "http.user_agent": None,
            "http.status_code": 500,
        }

        middleware_obj(django_request)

        span_list = self.memory_exporter.get_finished_spans()
        assert len(span_list) == 1
        assert span_list[0].name == "/error/"
        assert span_list[0].kind == trace_api.SpanKind.SERVER
        assert span_list[0].attributes == expected_attributes

    def test_blacklist_nospan(self):
        settings = type("Test", (object,), {})
        settings.OPENTELEMETRY = {
            "TRACE": {"BLACKLISTED_PATHS": ["/_ah/health/"]}
        }
        patch_settings = mock.patch("django.conf.settings", settings)

        with patch_settings:
            middleware_obj = OpenTelemetryTracingMiddleware(
                MockViewOk.as_view()
            )

        django_request = RequestFactory().get("/_ah/health/", **{})
        django_request.resolver_match = ResolverMatch(
            MockViewOk.as_view(), None, None
        )

        middleware_obj(django_request)

        span_list = self.memory_exporter.get_finished_spans()
        assert len(span_list) == 0


class TestDjangoIntegrationSubclassedMiddleware(WsgiTestBase):
    def setUp(self):
        super().setUp()
        if not django_settings.configured:
            django_settings.configure(ROOT_URLCONF=sys.modules[__name__])
        setup_test_environment()

    def tearDown(self):
        super().tearDown()
        teardown_test_environment()

    def test_customized_span_naming_get_200(self):
        django_settings.MIDDLEWARE = [__name__ + ".CustomMiddleware"]

        Client().get("/ok/")

        expected_attributes = {
            "http.method": "GET",
            "http.url": "http://testserver/ok/",
            "http.target": "/ok/",
            "http.host": None,
            "http.scheme": "http",
            "http.user_agent": None,
            "http.status_code": 200,
        }

        span_list = self.memory_exporter.get_finished_spans()
        assert len(span_list) == 1
        assert span_list[0].name == "tests.test_django_integration.MockViewOk"
        assert span_list[0].kind == trace_api.SpanKind.SERVER
        assert span_list[0].attributes == expected_attributes


if __name__ == "__main__":
    unittest.main()
