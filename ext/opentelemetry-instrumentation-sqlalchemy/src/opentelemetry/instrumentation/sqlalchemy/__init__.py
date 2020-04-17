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

"""Instrument sqlalchemy to report SQL queries.

There are two options for instrumenting code. The first option is to use
the `opentelemetry-auto-instrumentation` executable which will automatically
patch your SQLAlchemy engine. The second is to programmatically enable
instrumentation via the following code:
::
    from opentelemetry.instrumentation.sqlalchemy.patch import patch
    import sqlalchemy

    patch()
"""
from opentelemetry.auto_instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.instrumentation.sqlalchemy.patch import patch, unpatch


class SQLAlchemyInstrumentor(BaseInstrumentor):
    """An instrumentor for SQLAlchemy
    See `BaseInstrumentor`
    """

    def _instrument(self):
        patch()

    def _uninstrument(self):
        unpatch()
