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

import os

import jinja2

from opentelemetry import trace as trace_api
from opentelemetry.ext.jinja2 import Jinja2Instrumentor
from opentelemetry.test.test_base import TestBase
from opentelemetry.trace import get_tracer

TEST_DIR = os.path.dirname(os.path.realpath(__file__))
TMPL_DIR = os.path.join(TEST_DIR, "templates")


class TestJinja2Instrumentor(TestBase):
    def setUp(self):
        super().setUp()
        Jinja2Instrumentor().instrument()
        # prevent cache effects when using Template('code...')
        # pylint: disable=protected-access
        jinja2.environment._spontaneous_environments.clear()
        self.tracer = get_tracer(__name__)

    def tearDown(self):
        Jinja2Instrumentor().uninstrument()

    def test_render_inline_template(self):
        with self.tracer.start_as_current_span("test"):
            template = jinja2.environment.Template("Hello {{name}}!")
            self.assertEqual(template.render(name="Jinja"), "Hello Jinja!")

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 3)

        self.assertIs(spans[0].parent, spans[2].get_context())
        self.assertIs(spans[1].parent, spans[2].get_context())
        self.assertIsNone(spans[2].parent)

        self.assertEqual(spans[0].name, "jinja2.compile")
        self.assertIs(spans[0].kind, trace_api.SpanKind.INTERNAL)
        self.assertEqual(
            spans[0].attributes, {"jinja2.template_name": "<memory>"},
        )

        self.assertEqual(spans[1].name, "jinja2.render")
        self.assertEqual(spans[1].kind, trace_api.SpanKind.INTERNAL)
        self.assertEqual(
            spans[1].attributes, {"jinja2.template_name": "<memory>"},
        )

    def test_generate_inline_template(self):
        with self.tracer.start_as_current_span("test"):
            template = jinja2.environment.Template("Hello {{name}}!")
            self.assertEqual(
                "".join(template.generate(name="Jinja")), "Hello Jinja!"
            )

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 3)

        self.assertIs(spans[0].parent, spans[2].get_context())
        self.assertIs(spans[1].parent, spans[2].get_context())
        self.assertIsNone(spans[2].parent)

        self.assertEqual(spans[0].name, "jinja2.compile")
        self.assertEqual(spans[0].kind, trace_api.SpanKind.INTERNAL)
        self.assertEqual(
            spans[0].attributes, {"jinja2.template_name": "<memory>"},
        )

        self.assertEqual(spans[1].name, "jinja2.render")
        self.assertEqual(spans[1].kind, trace_api.SpanKind.INTERNAL)
        self.assertEqual(
            spans[1].attributes, {"jinja2.template_name": "<memory>"},
        )

    def test_file_template(self):
        with self.tracer.start_as_current_span("test"):
            loader = jinja2.loaders.FileSystemLoader(TMPL_DIR)
            env = jinja2.Environment(loader=loader)
            template = env.get_template("template.html")
            self.assertEqual(
                template.render(name="Jinja"), "Message: Hello Jinja!"
            )

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 6)

        self.assertEqual(spans[0].parent, spans[1].get_context())
        self.assertEqual(spans[1].parent, spans[5].get_context())
        self.assertEqual(spans[2].parent, spans[3].get_context())
        self.assertEqual(spans[3].parent, spans[4].get_context())
        self.assertEqual(spans[4].parent, spans[5].get_context())
        self.assertIsNone(spans[5].parent)

        self.assertEqual(spans[0].name, "jinja2.compile")
        self.assertEqual(spans[1].name, "jinja2.load")
        self.assertEqual(spans[2].name, "jinja2.compile")
        self.assertEqual(spans[3].name, "jinja2.load")
        self.assertEqual(spans[4].name, "jinja2.render")

        self.assertEqual(
            spans[0].attributes, {"jinja2.template_name": "template.html"},
        )
        self.assertEqual(
            spans[1].attributes,
            {
                "jinja2.template_name": "template.html",
                "jinja2.template_path": os.path.join(
                    TMPL_DIR, "template.html"
                ),
            },
        )
        self.assertEqual(
            spans[2].attributes, {"jinja2.template_name": "base.html"},
        )
        self.assertEqual(
            spans[3].attributes,
            {
                "jinja2.template_name": "base.html",
                "jinja2.template_path": os.path.join(TMPL_DIR, "base.html"),
            },
        )
        self.assertEqual(
            spans[4].attributes, {"jinja2.template_name": "template.html"},
        )

    def test_uninstrumented(self):
        Jinja2Instrumentor().uninstrument()

        jinja2.environment.Template("Hello {{name}}!")
        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 0)

        Jinja2Instrumentor().instrument()
