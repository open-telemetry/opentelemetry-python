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

from opentelemetry.ext.sqlalchemy.engine import trace_engine
from opentelemetry.test.test_base import TestBase


class TestSqlalchemyInstrumentation(TestBase):
    def test_trace_integration(self):
        engine = create_engine("sqlite:///:memory:")
        trace_engine(engine, self.tracer_provider, "my-database")
        cnx = engine.connect()
        cnx.execute("SELECT	1 + 1;").fetchall()
        spans = self.memory_exporter.get_finished_spans()

        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].name, "sqlite.query")
