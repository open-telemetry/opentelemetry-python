# Copyright 2019, OpenTelemetry Authors
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
The opentelemetry-ext-pymongo package allows tracing commands made by the
pymongo library.
"""

from pymongo import monitoring

from opentelemetry.trace import SpanKind, Span
from opentelemetry.trace.status import Status, StatusCanonicalCode

MODULE_NAME = 'pymongo'
DATA_BASE_TYPE = 'mongodb'

COMMAND_ATTRIBUTES = ['filter', 'sort', 'skip', 'limit', 'pipeline']


def trace_integration(tracer=None):
    """Integrate with pymongo to trace it using event listener.
       https://api.mongodb.com/python/current/api/pymongo/monitoring.html
    """
    monitoring.register(CommandTracer(tracer=tracer))


class CommandTracer(monitoring.CommandListener):
    def __init__(self, tracer=None):
        self._tracer = tracer

    def started(self, event):
        name: MODULE_NAME + "."+ event.command.get(event.command_name)

        with self._tracer.start_span(name, kind=SpanKind.CLIENT) as span:
            span.set_attribute("component", DATA_BASE_TYPE)
            span.set_attribute("db.type", DATA_BASE_TYPE)
            span.set_attribute("db.instance", event.database_name)
            span.set_attribute("db.statement", event.command.get(event.command_name))
            span.set_attribute("peer.address", str(event.connection_id))
            span.set_attribute("peer.hostname", str(event.connection_id)) #TODO: calculate this
            span.set_attribute("peer.port", str(event.connection_id)) #TODO: calculate this
            span.set_attribute("operation_id", event.operation_id)

            for attr in COMMAND_ATTRIBUTES:
                _attr = event.command.get(attr)
                if _attr is not None:
                    span.set_attribute(attr, str(_attr))
                    
    def succeeded(self, event):
        self._endSpan(event, True)

    def failed(self, event):
        self._endSpan(event, False)

    def _endSpan(self, event, succeeded):
        span = self._tracer.current_span()
        span.set_attribute("request_id", event.request_id)
        span.set_attribute("duration_micros", event.duration_micros)
        if succeeded:
            span.set_status(Status(StatusCanonicalCode.OK, event.reply))
        else:
            span.set_status(Status(StatusCanonicalCode.UNKNOWN, event.failure))
        self._tracer.end_span()
