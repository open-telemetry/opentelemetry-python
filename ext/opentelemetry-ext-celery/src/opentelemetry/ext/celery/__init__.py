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
Instrument `celery`_ to trace Celery applications.

.. _celery: https://pypi.org/project/celery/

Usage
-----

* Start broker backend

.. code::

    docker run -p 5672:5672 rabbitmq


* Run instrumented task

.. code:: python

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
import signal

from celery import signals  # pylint: disable=no-name-in-module

from opentelemetry import trace
from opentelemetry.ext.celery import utils
from opentelemetry.ext.celery.version import __version__
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace.status import Status, StatusCanonicalCode

logger = logging.getLogger(__name__)

# Task operations
_TASK_TAG_KEY = "celery.action"
_TASK_APPLY_ASYNC = "apply_async"
_TASK_RUN = "run"

_TASK_RETRY_REASON_KEY = "celery.retry.reason"
_TASK_REVOKED_REASON_KEY = "celery.revoked.reason"
_TASK_REVOKED_TERMINATED_SIGNAL_KEY = "celery.terminated.signal"
_TASK_NAME_KEY = "celery.task_name"
_MESSAGE_ID_ATTRIBUTE_NAME = "messaging.message_id"


class CeleryInstrumentor(BaseInstrumentor):
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
        task = utils.retrieve_task(kwargs)
        task_id = utils.retrieve_task_id(kwargs)

        if task is None or task_id is None:
            return

        logger.debug("prerun signal start task_id=%s", task_id)

        span = self._tracer.start_span(task.name, kind=trace.SpanKind.CONSUMER)

        activation = self._tracer.use_span(span, end_on_exit=True)
        activation.__enter__()
        utils.attach_span(task, task_id, (span, activation))

    @staticmethod
    def _trace_postrun(*args, **kwargs):
        task = utils.retrieve_task(kwargs)
        task_id = utils.retrieve_task_id(kwargs)

        if task is None or task_id is None:
            return

        logger.debug("postrun signal task_id=%s", task_id)

        # retrieve and finish the Span
        span, activation = utils.retrieve_span(task, task_id)
        if span is None:
            logger.warning("no existing span found for task_id=%s", task_id)
            return

        # request context tags
        span.set_attribute(_TASK_TAG_KEY, _TASK_RUN)
        utils.set_attributes_from_context(span, kwargs)
        utils.set_attributes_from_context(span, task.request)
        span.set_attribute(_TASK_NAME_KEY, task.name)

        activation.__exit__(None, None, None)
        utils.detach_span(task, task_id)

    def _trace_before_publish(self, *args, **kwargs):
        task = utils.retrieve_task_from_sender(kwargs)
        task_id = utils.retrieve_task_id_from_message(kwargs)

        if task is None or task_id is None:
            return

        span = self._tracer.start_span(task.name, kind=trace.SpanKind.PRODUCER)

        # apply some attributes here because most of the data is not available
        span.set_attribute(_TASK_TAG_KEY, _TASK_APPLY_ASYNC)
        span.set_attribute(_MESSAGE_ID_ATTRIBUTE_NAME, task_id)
        span.set_attribute(_TASK_NAME_KEY, task.name)
        utils.set_attributes_from_context(span, kwargs)

        activation = self._tracer.use_span(span, end_on_exit=True)
        activation.__enter__()
        utils.attach_span(task, task_id, (span, activation), is_publish=True)

    @staticmethod
    def _trace_after_publish(*args, **kwargs):
        task = utils.retrieve_task_from_sender(kwargs)
        task_id = utils.retrieve_task_id_from_message(kwargs)

        if task is None or task_id is None:
            return

        # retrieve and finish the Span
        _, activation = utils.retrieve_span(task, task_id, is_publish=True)
        if activation is None:
            logger.warning("no existing span found for task_id=%s", task_id)
            return

        activation.__exit__(None, None, None)
        utils.detach_span(task, task_id, is_publish=True)

    @staticmethod
    def _trace_failure(*args, **kwargs):
        task = utils.retrieve_task_from_sender(kwargs)
        task_id = utils.retrieve_task_id(kwargs)

        if task is None or task_id is None:
            return

        # retrieve and pass exception info to activation
        span, _ = utils.retrieve_span(task, task_id)
        if span is None:
            return

        status_kwargs = {"canonical_code": StatusCanonicalCode.UNKNOWN}

        ex = kwargs.get("einfo")

        if (
            hasattr(task, "throws")
            and ex is not None
            and isinstance(ex.exception, task.throws)
        ):
            return

        if ex is not None:
            status_kwargs["description"] = str(ex)

        span.set_status(Status(**status_kwargs))

    @staticmethod
    def _trace_retry(*args, **kwargs):
        task = utils.retrieve_task_from_sender(kwargs)
        task_id = utils.retrieve_task_id_from_request(kwargs)
        reason = utils.retrieve_reason(kwargs)

        if task is None or task_id is None or reason is None:
            return

        span, _ = utils.retrieve_span(task, task_id)
        if span is None:
            return

        # Add retry reason metadata to span
        # Use `str(reason)` instead of `reason.message` in case we get
        # something that isn't an `Exception`
        span.set_attribute(_TASK_RETRY_REASON_KEY, str(reason))
