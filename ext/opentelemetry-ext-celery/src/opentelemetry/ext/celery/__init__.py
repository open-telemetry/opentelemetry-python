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
"""
Instrument `celery`_ to report Celery APP operations.

There are two options for instrumenting code. The first option is to use the
``opentelemetry-auto-instrumentation`` executable which will automatically
instrument your Celery APP. The second is to programmatically enable
instrumentation as explained in the following section.

.. _celery: https://pypi.org/project/celery/

Usage
-----

Be sure rabbitmq is running:

.. code::

    docker run -p 5672:5672 rabbitmq

.. code:: python

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider

    trace.set_tracer_provider(TracerProvider())
    # TODO: configure span exporters

    from opentelemetry.ext.celery import CeleryInstrumentor
    CeleryInstrumentor().instrument()

    from celery import Celery

    app = Celery("tasks", broker="amqp://localhost")

    @app.task
    def add(x, y):
        return x + y

    add.delay(42, 50)

API
---
"""

import logging

from celery import registry, signals

from opentelemetry import trace
from opentelemetry.auto_instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.ext.celery.utils import (
    attach_span,
    detach_span,
    retrieve_span,
    retrieve_task_id,
    set_attributes_from_context,
)
from opentelemetry.ext.celery.version import __version__
from opentelemetry.trace.status import Status, StatusCanonicalCode

logger = logging.getLogger(__name__)

# Task operations
_TASK_TAG_KEY = "celery.action"
_TASK_APPLY_ASYNC = "apply_async"
_TASK_RUN = "run"

_TASK_RETRY_REASON_KEY = "celery.retry.reason"
_TASK_NAME_KEY = "celery.task_name"
_MESSAGE_ID_ATTRIBUTE_NAME = "messaging.message_id"


class CeleryInstrumentor(BaseInstrumentor):
    # pylint: disable=unused-argument
    def _instrument(self, **kwargs):
        tracer_provider = kwargs.get("tracer_provider")

        # pylint: disable=attribute-defined-outside-init
        self._tracer = trace.get_tracer(__name__, __version__, tracer_provider)

        signals.task_prerun.connect(self._trace_prerun, weak=False)
        signals.task_postrun.connect(self._trace_postrun, weak=False)
        signals.before_task_publish.connect(
            self._trace_before_publish, weak=False
        )
        signals.after_task_publish.connect(
            self._trace_after_publish, weak=False
        )
        signals.task_failure.connect(self._trace_failure, weak=False)
        signals.task_retry.connect(self._trace_retry, weak=False)

    def _uninstrument(self, **kwargs):
        signals.task_prerun.disconnect(self._trace_prerun)
        signals.task_postrun.disconnect(self._trace_postrun)
        signals.before_task_publish.disconnect(self._trace_before_publish)
        signals.after_task_publish.disconnect(self._trace_after_publish)
        signals.task_failure.disconnect(self._trace_failure)
        signals.task_retry.disconnect(self._trace_retry)

    def _trace_prerun(self, *args, **kwargs):
        task = kwargs.get("task")
        task_id = kwargs.get("task_id")
        logger.debug("prerun signal start task_id=%s", task_id)
        if task is None or task_id is None:
            logger.debug(
                "Unable to extract the Task and the task_id. This version of Celery may not be supported."
            )
            return

        # TODO: When the span could be SERVER?
        span = self._tracer.start_span(task.name, kind=trace.SpanKind.CONSUMER)

        activation = self._tracer.use_span(span, end_on_exit=True)
        activation.__enter__()
        attach_span(task, task_id, (span, activation))

    @staticmethod
    def _trace_postrun(*args, **kwargs):
        task = kwargs.get("task")
        task_id = kwargs.get("task_id")
        logger.debug("postrun signal task_id=%s", task_id)
        if task is None or task_id is None:
            logger.debug(
                "Unable to extract the Task and the task_id. This version of Celery may not be supported."
            )
            return

        # retrieve and finish the Span
        span, activation = retrieve_span(task, task_id)
        if span is None:
            logger.warning("no existing span found for task_id=%s", task_id)
            return

        # request context tags
        span.set_attribute(_TASK_TAG_KEY, _TASK_RUN)
        set_attributes_from_context(span, kwargs)
        set_attributes_from_context(span, task.request)
        span.set_attribute(_TASK_NAME_KEY, task.name)

        activation.__exit__(None, None, None)
        detach_span(task, task_id)

    def _trace_before_publish(self, *args, **kwargs):
        # The `Task` instance **does not** include any information about the current
        # execution, so it **must not** be used to retrieve `request` data.
        # pylint: disable=no-member
        task = registry.tasks.get(kwargs.get("sender"))
        task_id = retrieve_task_id(kwargs)

        if task is None or task_id is None:
            logger.debug(
                "Unable to extract the Task and the task_id. This version of Celery may not be supported."
            )
            return

        # TODO: When the span could be CLIENT?
        span = self._tracer.start_span(task.name, kind=trace.SpanKind.PRODUCER)

        # apply some attributes here because most of the data is not available
        span.set_attribute(_TASK_TAG_KEY, _TASK_APPLY_ASYNC)
        span.set_attribute(_MESSAGE_ID_ATTRIBUTE_NAME, task_id)
        span.set_attribute(_TASK_NAME_KEY, task.name)
        set_attributes_from_context(span, kwargs)

        activation = self._tracer.use_span(span, end_on_exit=True)
        activation.__enter__()
        attach_span(task, task_id, (span, activation), is_publish=True)

    @staticmethod
    def _trace_after_publish(*args, **kwargs):
        # pylint: disable=no-member
        task = registry.tasks.get(kwargs.get("sender"))
        task_id = retrieve_task_id(kwargs)
        if task is None or task_id is None:
            logger.debug(
                "Unable to extract the Task and the task_id. This version of Celery may not be supported."
            )
            return

        # retrieve and finish the Span
        _, activation = retrieve_span(task, task_id, is_publish=True)
        if activation is None:
            logger.warning("no existing span found for task_id=%s", task_id)
            return

        activation.__exit__(None, None, None)
        detach_span(task, task_id, is_publish=True)

    @staticmethod
    def _trace_failure(*args, **kwargs):
        task = kwargs.get("sender")
        task_id = kwargs.get("task_id")
        if task is None or task_id is None:
            logger.debug(
                "Unable to extract the Task and the task_id. This version of Celery may not be supported."
            )
            return

        # retrieve and pass exception info to activation
        span, _ = retrieve_span(task, task_id)
        if span is None:
            return

        ex = kwargs.get("einfo")
        if ex is None:
            return
        if hasattr(task, "throws") and isinstance(ex.exception, task.throws):
            return

        span.set_status(
            Status(
                canonical_code=StatusCanonicalCode.UNKNOWN,
                description=str(ex),
            )
        )

    @staticmethod
    def _trace_retry(*args, **kwargs):
        task = kwargs.get("sender")
        context = kwargs.get("request")
        if task is None or context is None:
            logger.debug(
                "Unable to extract the Task or the Context. This version of Celery may not be supported."
            )
            return

        reason = kwargs.get("reason")
        if not reason:
            logger.debug(
                "Unable to extract the retry reason. This version of Celery may not be supported."
            )
            return

        span, _ = retrieve_span(task, context.id)
        if span is None:
            return

        # Add retry reason metadata to span
        # Use `str(reason)` instead of `reason.message` in case we get
        # something that isn't an `Exception`
        span.set_attribute(_TASK_RETRY_REASON_KEY, str(reason))
