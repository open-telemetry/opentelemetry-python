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

from opentelemetry.trace import SpanKind
from opentelemetry.trace.status import Status, StatusCanonicalCode

DATABASE_TYPE = "mongodb"
COMMAND_ATTRIBUTES = ["filter", "sort", "skip", "limit", "pipeline"]


def trace_integration(tracer=None):
    """Integrate with pymongo to trace it using event listener.
       https://api.mongodb.com/python/current/api/pymongo/monitoring.html
    """

    monitoring.register(CommandTracer(tracer))


class CommandTracer(monitoring.CommandListener):
    def __init__(self, tracer):
        if tracer is None:
            raise ValueError("The tracer is not provided.")
        self._tracer = tracer
        self._span = None

    def started(self, event: monitoring.CommandStartedEvent):
        command = event.command.get(event.command_name)
        if command is None:
            command = ""
        name = DATABASE_TYPE + "." + event.command_name + "." + command
        self._span = None
        try:
            self._span = self._tracer.start_span(name, kind=SpanKind.CLIENT)
            self._span.set_attribute("component", DATABASE_TYPE)
            self._span.set_attribute("db.type", DATABASE_TYPE)
            self._span.set_attribute("db.instance", event.database_name)
            self._span.set_attribute(
                "db.statement", event.command_name + " " + command
            )
            if event.connection_id is not None:
                self._span.set_attribute(
                    "peer.hostname", event.connection_id[0]
                )
                self._span.set_attribute("peer.port", event.connection_id[1])

            # pymongo specific, not specified by spec
            self._span.set_attribute(
                "db.mongo.operation_id", event.operation_id
            )
            self._span.set_attribute("db.mongo.request_id", event.request_id)

            for attr in COMMAND_ATTRIBUTES:
                _attr = event.command.get(attr)
                if _attr is not None:
                    self._span.set_attribute("db.mongo." + attr, str(_attr))
        except Exception as ex:  # noqa pylint: disable=broad-except
            if self._span is not None:
                self._span.set_status(Status(StatusCanonicalCode.INTERNAL, ex))
                self._span.end()

    def succeeded(self, event: monitoring.CommandSucceededEvent):
        if self._span is not None:
            self._span.set_attribute(
                "db.mongo.duration_micros", event.duration_micros
            )
            self._span.set_status(Status(StatusCanonicalCode.OK, event.reply))
            self._span.end()

    def failed(self, event: monitoring.CommandFailedEvent):
        if self._span is not None:
            self._span.set_attribute(
                "db.mongo.duration_micros", event.duration_micros
            )
            self._span.set_status(
                Status(StatusCanonicalCode.UNKNOWN, event.failure)
            )
            self._span.end()
