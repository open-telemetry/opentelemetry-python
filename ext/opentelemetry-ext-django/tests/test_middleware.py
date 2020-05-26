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
from unittest.mock import patch

from django.conf import settings
from django.conf.urls import url
from django.test import Client
from django.test.utils import setup_test_environment, teardown_test_environment

from opentelemetry.configuration import Configuration
from opentelemetry.ext.django import DjangoInstrumentor
from opentelemetry.test.wsgitestutil import WsgiTestBase
from opentelemetry.trace import SpanKind
from opentelemetry.trace.status import StatusCanonicalCode

# pylint: disable=import-error
from .views import error, excluded, excluded2, traced

urlpatterns = [
    url(r"^traced/", traced),
    url(r"^error/", error),
    url(r"^excluded/", excluded),
    url(r"^excluded2/", excluded2),
]
_django_instrumentor = DjangoInstrumentor()


class TestMiddleware(WsgiTestBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        settings.configure(ROOT_URLCONF=modules[__name__])

    def setUp(self):
        super().setUp()
        setup_test_environment()
        _django_instrumentor.instrument()
        Configuration._reset()  # pylint: disable=protected-access

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
        self.assertEqual(
            span.status.canonical_code, StatusCanonicalCode.UNKNOWN
        )
        self.assertEqual(span.attributes["http.method"], "GET")
        self.assertEqual(
            span.attributes["http.url"], "http://testserver/error/"
        )
        self.assertEqual(span.attributes["http.scheme"], "http")

    @patch.dict(
        "os.environ",  # type: ignore
        {
            "OPENTELEMETRY_PYTHON_DJANGO_EXCLUDED_HOSTS": (
                "http://testserver/excluded/"
            ),
            "OPENTELEMETRY_PYTHON_DJANGO_EXCLUDED_PATHS": "excluded2/",
        },
    )
    def test_exclude(self):
        Client().get("/traced/")
        Client().get("/excluded/")
        Client().get("/excluded2/")

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
