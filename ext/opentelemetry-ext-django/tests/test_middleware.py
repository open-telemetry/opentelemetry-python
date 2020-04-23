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

from sys import modules

from django.test import Client
from django.conf import settings
from django.conf.urls import url
from django.test.utils import (
    setup_test_environment, teardown_test_environment
)

from opentelemetry.trace import SpanKind
from opentelemetry.trace.status import StatusCanonicalCode
from opentelemetry.test.wsgitestutil import WsgiTestBase
from opentelemetry.ext.django import DjangoInstrumentor

from .views import error, traced  # pylint: disable=import-error

urlpatterns = [
    url(r"^traced/", traced),
    url(r"^error/", error),
]
_django_instrumentor = DjangoInstrumentor()


# class TestDjangoOpenTracingMiddleware(WsgiTestBase, SimpleTestCase):
class TestDjangoOpenTracingMiddleware(WsgiTestBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        settings.configure(ROOT_URLCONF=modules[__name__])

    def setUp(self):
        super().setUp()
        setup_test_environment()
        _django_instrumentor.instrument()

    def tearDown(self):
        super().tearDown()
        teardown_test_environment()
        _django_instrumentor.uninstrument()

    def test_traced_get(self):
        Client().get("/traced/")

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)

        span = spans[0]

        self.assertEqual(span.name, "traced")
        self.assertEqual(span.kind, SpanKind.SERVER)
        self.assertEqual(span.status.canonical_code, StatusCanonicalCode.OK)
        self.assertEqual(span.attributes["http.method"], "GET")
        self.assertEqual(
            span.attributes["http.url"], "http://testserver/traced/"
        )
        self.assertEqual(span.attributes["http.scheme"], "http")
        self.assertEqual(span.attributes["http.status_code"], 200)
        self.assertEqual(span.attributes["http.status_text"], "OK")

    def test_traced_post(self):
        Client().post("/traced/")

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)

        span = spans[0]

        self.assertEqual(span.name, "traced")
        self.assertEqual(span.kind, SpanKind.SERVER)
        self.assertEqual(span.status.canonical_code, StatusCanonicalCode.OK)
        self.assertEqual(span.attributes["http.method"], "POST")
        self.assertEqual(
            span.attributes["http.url"], "http://testserver/traced/"
        )
        self.assertEqual(span.attributes["http.scheme"], "http")
        self.assertEqual(span.attributes["http.status_code"], 200)
        self.assertEqual(span.attributes["http.status_text"], "OK")

    def test_error(self):
        with self.assertRaises(ValueError):
            Client().get("/error/")

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)

        span = spans[0]

        self.assertEqual(span.name, "error")
        self.assertEqual(span.kind, SpanKind.SERVER)
        self.assertEqual(span.status.canonical_code, StatusCanonicalCode.OK)
        self.assertEqual(span.attributes["http.method"], "POST")
        self.assertEqual(
            span.attributes["http.url"], "http://testserver/traced/"
        )
        self.assertEqual(span.attributes["http.scheme"], "http")
        self.assertEqual(span.attributes["http.status_code"], 500)
        # FIXME should the status_text be "OK"
        self.assertEqual(span.attributes["http.status_text"], "OK")
