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

    def test_middleware_traced(self):
        Client().get("/traced/")
        self.assertEqual(len(self.memory_exporter.get_finished_spans()), 1)

    def test_middleware_error(self):
        with self.assertRaises(ValueError):
            Client().get("/error/")
        self.assertEqual(len(self.memory_exporter.get_finished_spans()), 1)
