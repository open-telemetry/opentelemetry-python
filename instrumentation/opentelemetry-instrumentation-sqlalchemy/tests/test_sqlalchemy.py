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

from sqlalchemy import create_engine

from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.test.test_base import TestBase


class TestSqlalchemyInstrumentation(TestBase):
    def tearDown(self):
        super().tearDown()
        SQLAlchemyInstrumentor().uninstrument()

    def test_trace_integration(self):
        engine = create_engine("sqlite:///:memory:")
        SQLAlchemyInstrumentor().instrument(
            engine=engine,
            tracer_provider=self.tracer_provider,
            service="my-database",
        )
        cnx = engine.connect()
        cnx.execute("SELECT	1 + 1;").fetchall()
        spans = self.memory_exporter.get_finished_spans()

        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].name, "sqlite.query")

    def test_create_engine_wrapper(self):
        SQLAlchemyInstrumentor().instrument()
        from sqlalchemy import create_engine  # pylint: disable-all

        engine = create_engine("sqlite:///:memory:")
        cnx = engine.connect()
        cnx.execute("SELECT	1 + 1;").fetchall()
        spans = self.memory_exporter.get_finished_spans()

        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].name, "sqlite.query")
