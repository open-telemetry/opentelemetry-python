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
The integration with MongoDB supports the `pymongo`_ library and is specified
to ``trace_integration`` using ``'pymongo'``.

.. _pymongo: https://pypi.org/project/pymongo

Usage
-----

.. code:: python

    from pymongo import MongoClient
    from opentelemetry.trace import tracer_provider
    from opentelemetry.trace.ext.pymongo import trace_integration

    trace_integration(tracer_provider())
    client = MongoClient()
    db = client["MongoDB_Database"]
    collection = db["MongoDB_Collection"]
    collection.find_one()

API
---
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
        self._span_dict = {}

    def started(self, event: monitoring.CommandStartedEvent):
        """ Method to handle a pymongo CommandStartedEvent """
        command = event.command.get(event.command_name, "")
        name = DATABASE_TYPE + "." + event.command_name
        statement = event.command_name
        if command:
            name += "." + command
            statement += " " + command

        try:
            span = self._tracer.start_span(name, kind=SpanKind.CLIENT)
            span.set_attribute("component", DATABASE_TYPE)
            span.set_attribute("db.type", DATABASE_TYPE)
            span.set_attribute("db.instance", event.database_name)
            span.set_attribute("db.statement", statement)
            if event.connection_id is not None:
                span.set_attribute("net.peer.name", event.connection_id[0])
                span.set_attribute("net.peer.port", event.connection_id[1])

            # pymongo specific, not specified by spec
            span.set_attribute("db.mongo.operation_id", event.operation_id)
            span.set_attribute("db.mongo.request_id", event.request_id)

            for attr in COMMAND_ATTRIBUTES:
                _attr = event.command.get(attr)
                if _attr is not None:
                    span.set_attribute("db.mongo." + attr, str(_attr))

            # Add Span to dictionary
            self._span_dict[_get_span_dict_key(event)] = span
        except Exception as ex:  # noqa pylint: disable=broad-except
            if span is not None:
                span.set_status(Status(StatusCanonicalCode.INTERNAL, str(ex)))
                span.end()
                self._remove_span(event)

    def succeeded(self, event: monitoring.CommandSucceededEvent):
        """ Method to handle a pymongo CommandSucceededEvent """
        span = self._get_span(event)
        if span is not None:
            span.set_attribute(
                "db.mongo.duration_micros", event.duration_micros
            )
            span.set_status(Status(StatusCanonicalCode.OK, event.reply))
            span.end()
            self._remove_span(event)

    def failed(self, event: monitoring.CommandFailedEvent):
        """ Method to handle a pymongo CommandFailedEvent """
        span = self._get_span(event)
        if span is not None:
            span.set_attribute(
                "db.mongo.duration_micros", event.duration_micros
            )
            span.set_status(Status(StatusCanonicalCode.UNKNOWN, event.failure))
            span.end()
            self._remove_span(event)

    def _get_span(self, event):
        return self._span_dict.get(_get_span_dict_key(event))

    def _remove_span(self, event):
        self._span_dict.pop(_get_span_dict_key(event))


def _get_span_dict_key(event):
    if event.connection_id is not None:
        return (event.request_id, event.connection_id)
    return event.request_id
