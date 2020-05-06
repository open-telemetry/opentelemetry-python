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

# Celery Context key
CTX_KEY = "__otel_task_span"


# pylint:disable=too-many-branches
def set_attributes_from_context(span, context):
    """Helper to extract meta values from a Celery Context"""

    attribute_keys = (
        "compression",
        "correlation_id",
        "countdown",
        "delivery_info",
        "declare",
        "eta",
        "exchange",
        "expires",
        "hostname",
        "id",
        "priority",
        "queue",
        "reply_to",
        "retries",
        "routing_key",
        "serializer",
        "timelimit",
        "origin",
        "state",
    )

    for key in attribute_keys:
        value = context.get(key)

        # Skip this key if it is not set
        if value is None or value == "":
            continue

        # Skip `timelimit` if it is not set (it's default/unset value is a
        # tuple or a list of `None` values
        if key == "timelimit" and value in [(None, None), [None, None]]:
            continue

        # Skip `retries` if it's value is `0`
        if key == "retries" and value == 0:
            continue

        # Celery 4.0 uses `origin` instead of `hostname`; this change preserves
        # the same name for the tag despite Celery version
        if key == "origin":
            key = "hostname"

        # TODO: hack to avoid bad attribute type
        if key == "delivery_info":
            # Get also destination from this
            routing_key = value.get("routing_key")
            if routing_key:
                span.set_attribute("messaging.destination", routing_key)
            value = str(value)

        # prefix the tag as 'celery'
        attribute_name = "celery.{}".format(key)

        if key == "id":
            attribute_name = "messaging.message_id"

        if key == "correlation_id":
            attribute_name = "messaging.conversation_id"

        if key == "routing_key":
            attribute_name = "messaging.destination"

        # according to https://docs.celeryproject.org/en/stable/userguide/routing.html#exchange-types
        if key == "declare":
            attribute_name = "messaging.destination_kind"
            for declare in value:
                if declare.exchange.type == "direct":
                    value = "queue"
                    break
                if declare.exchange.type == "topic":
                    value = "topic"
                    break

        span.set_attribute(attribute_name, value)


def attach_span(task, task_id, span, is_publish=False):
    """Helper to propagate a `Span` for the given `Task` instance. This
    function uses a `dict` that stores the Span using the
    `(task_id, is_publish)` as a key. This is useful when information must be
    propagated from one Celery signal to another.

    We use (task_id, is_publish) for the key to ensure that publishing a
    task from within another task does not cause any conflicts.

    This mostly happens when either a task fails and a retry policy is in place,
    or when a task is manually retries (e.g. `task.retry()`), we end up trying
    to publish a task with the same id as the task currently running.

    Previously publishing the new task would overwrite the existing `celery.run` span
    in the `dict` causing that span to be forgotten and never finished
    NOTE: We cannot test for this well yet, because we do not run a celery worker,
    and cannot run `task.apply_async()`
    """
    span_dict = getattr(task, CTX_KEY, None)
    if span_dict is None:
        span_dict = dict()
        setattr(task, CTX_KEY, span_dict)

    span_dict[(task_id, is_publish)] = span


def detach_span(task, task_id, is_publish=False):
    """Helper to remove a `Span` in a Celery task when it's propagated.
    This function handles tasks where the `Span` is not attached.
    """
    span_dict = getattr(task, CTX_KEY, None)
    if span_dict is None:
        return

    # See note in `attach_span` for key info
    span_dict.pop((task_id, is_publish), (None, None))


def retrieve_span(task, task_id, is_publish=False):
    """Helper to retrieve an active `Span` stored in a `Task`
    instance
    """
    span_dict = getattr(task, CTX_KEY, None)
    if span_dict is None:
        return (None, None)

    # See note in `attach_span` for key info
    return span_dict.get((task_id, is_publish), (None, None))


def retrieve_task_id(context):
    """Helper to retrieve the `Task` identifier from the message `body`.
    This helper supports Protocol Version 1 and 2. The Protocol is well
    detailed in the official documentation:
    http://docs.celeryproject.org/en/latest/internals/protocol.html
    """
    headers = context.get("headers")
    body = context.get("body")
    if headers:
        # Protocol Version 2 (default from Celery 4.0)
        return headers.get("id")
    # Protocol Version 1
    return body.get("id")
