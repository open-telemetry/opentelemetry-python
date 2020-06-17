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

import unittest
from unittest import mock

from celery import Celery

from opentelemetry import trace as trace_api
from opentelemetry.ext.celery import utils
from opentelemetry.sdk import trace


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.app = Celery("celery.test_app")

    def test_set_attributes_from_context(self):
        # it should extract only relevant keys
        context = {
            "correlation_id": "44b7f305",
            "delivery_info": {"eager": True},
            "eta": "soon",
            "expires": "later",
            "hostname": "localhost",
            "id": "44b7f305",
            "reply_to": "44b7f305",
            "retries": 4,
            "timelimit": ("now", "later"),
            "custom_meta": "custom_value",
            "routing_key": "celery",
        }

        span = trace.Span("name", mock.Mock(spec=trace_api.SpanContext))
        utils.set_attributes_from_context(span, context)

        self.assertEqual(
            span.attributes.get("messaging.message_id"), "44b7f305"
        )
        self.assertEqual(
            span.attributes.get("messaging.conversation_id"), "44b7f305"
        )
        self.assertEqual(
            span.attributes.get("messaging.destination"), "celery"
        )

        self.assertEqual(
            span.attributes["celery.delivery_info"], str({"eager": True})
        )
        self.assertEqual(span.attributes.get("celery.eta"), "soon")
        self.assertEqual(span.attributes.get("celery.expires"), "later")
        self.assertEqual(span.attributes.get("celery.hostname"), "localhost")

        self.assertEqual(span.attributes.get("celery.reply_to"), "44b7f305")
        self.assertEqual(span.attributes.get("celery.retries"), 4)
        self.assertEqual(
            span.attributes.get("celery.timelimit"), ("now", "later")
        )
        self.assertNotIn("custom_meta", span.attributes)

    def test_set_attributes_from_context_empty_keys(self):
        # it should not extract empty keys
        context = {
            "correlation_id": None,
            "exchange": "",
            "timelimit": (None, None),
            "retries": 0,
        }

        span = trace.Span("name", mock.Mock(spec=trace_api.SpanContext))
        utils.set_attributes_from_context(span, context)

        self.assertEqual(len(span.attributes), 0)
        # edge case: `timelimit` can also be a list of None values
        context = {
            "timelimit": [None, None],
        }

        utils.set_attributes_from_context(span, context)

        self.assertEqual(len(span.attributes), 0)

    def test_span_propagation(self):
        # ensure spans getter and setter works properly
        @self.app.task
        def fn_task():
            return 42

        # propagate and retrieve a Span
        task_id = "7c6731af-9533-40c3-83a9-25b58f0d837f"
        span = trace.Span("name", mock.Mock(spec=trace_api.SpanContext))
        utils.attach_span(fn_task, task_id, span)
        span_after = utils.retrieve_span(fn_task, task_id)
        self.assertIs(span, span_after)

    def test_span_delete(self):
        # ensure the helper removes properly a propagated Span
        @self.app.task
        def fn_task():
            return 42

        # propagate a Span
        task_id = "7c6731af-9533-40c3-83a9-25b58f0d837f"
        span = trace.Span("name", mock.Mock(spec=trace_api.SpanContext))
        utils.attach_span(fn_task, task_id, span)
        # delete the Span
        utils.detach_span(fn_task, task_id)
        self.assertEqual(utils.retrieve_span(fn_task, task_id), (None, None))

    def test_span_delete_empty(self):
        # ensure detach_span doesn't raise an exception if span is not present
        @self.app.task
        def fn_task():
            return 42

        # delete the Span
        task_id = "7c6731af-9533-40c3-83a9-25b58f0d837f"
        try:
            utils.detach_span(fn_task, task_id)
            self.assertEqual(
                utils.retrieve_span(fn_task, task_id), (None, None)
            )
        except Exception as ex:  # pylint: disable=broad-except
            self.fail("Exception was raised: %s" % ex)

    def test_task_id_from_protocol_v1(self):
        # ensures a `task_id` is properly returned when Protocol v1 is used.
        # `context` is an example of an emitted Signal with Protocol v1
        context = {
            "body": {
                "expires": None,
                "utc": True,
                "args": ["user"],
                "chord": None,
                "callbacks": None,
                "errbacks": None,
                "taskset": None,
                "id": "dffcaec1-dd92-4a1a-b3ab-d6512f4beeb7",
                "retries": 0,
                "task": "tests.contrib.celery.test_integration.fn_task_parameters",
                "timelimit": (None, None),
                "eta": None,
                "kwargs": {"force_logout": True},
            },
            "sender": "tests.contrib.celery.test_integration.fn_task_parameters",
            "exchange": "celery",
            "routing_key": "celery",
            "retry_policy": None,
            "headers": {},
            "properties": {},
        }

        task_id = utils.retrieve_task_id_from_message(context)
        self.assertEqual(task_id, "dffcaec1-dd92-4a1a-b3ab-d6512f4beeb7")

    def test_task_id_from_protocol_v2(self):
        # ensures a `task_id` is properly returned when Protocol v2 is used.
        # `context` is an example of an emitted Signal with Protocol v2
        context = {
            "body": (
                ["user"],
                {"force_logout": True},
                {
                    u"chord": None,
                    u"callbacks": None,
                    u"errbacks": None,
                    u"chain": None,
                },
            ),
            "sender": u"tests.contrib.celery.test_integration.fn_task_parameters",
            "exchange": u"",
            "routing_key": u"celery",
            "retry_policy": None,
            "headers": {
                u"origin": u"gen83744@hostname",
                u"root_id": "7e917b83-4018-431d-9832-73a28e1fb6c0",
                u"expires": None,
                u"shadow": None,
                u"id": "7e917b83-4018-431d-9832-73a28e1fb6c0",
                u"kwargsrepr": u"{'force_logout': True}",
                u"lang": u"py",
                u"retries": 0,
                u"task": u"tests.contrib.celery.test_integration.fn_task_parameters",
                u"group": None,
                u"timelimit": [None, None],
                u"parent_id": None,
                u"argsrepr": u"['user']",
                u"eta": None,
            },
            "properties": {
                u"reply_to": "c3054a07-5b28-3855-b18c-1623a24aaeca",
                u"correlation_id": "7e917b83-4018-431d-9832-73a28e1fb6c0",
            },
        }

        task_id = utils.retrieve_task_id_from_message(context)
        self.assertEqual(task_id, "7e917b83-4018-431d-9832-73a28e1fb6c0")
