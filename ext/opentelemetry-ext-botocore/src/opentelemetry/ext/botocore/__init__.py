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
Instrumentation for Botocore
"""

import logging

from botocore.client import BaseClient
from wrapt import ObjectProxy, wrap_function_wrapper

from opentelemetry.auto_instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.ext.botocore.version import __version__
from opentelemetry.trace import SpanKind, get_tracer

logger = logging.getLogger(__name__)

ARGS_NAME = ("action", "params", "path", "verb")
TRACED_ARGS = ["params", "path", "verb"]


class BotoInstrumentor(BaseInstrumentor):
    """A instrumentor for Botocore

    See `BaseInstrumentor`
    """

    def _instrument(self, **kwargs):

        # FIXME should the tracer provider be accessed via Configuration
        # instead?
        # pylint: disable=attribute-defined-outside-init
        self._tracer = get_tracer(
            __name__, __version__, kwargs.get("tracer_provider")
        )

        wrap_function_wrapper(
            "botocore.client",
            "BaseClient._make_api_call",
            self._patched_api_call,
        )

    def _uninstrument(self, **kwargs):
        unwrap(BaseClient, "_make_api_call")

    def _patched_api_call(self, original_func, instance, args, kwargs):

        endpoint_name = deep_getattr(instance, "_endpoint._endpoint_prefix")

        with self._tracer.start_as_current_span(
            "{}.command".format(endpoint_name), kind=SpanKind.CONSUMER,
        ) as span:

            operation = None
            if args:
                operation = args[0]
                span.resource = "%s.%s" % (endpoint_name, operation.lower())

            else:
                span.resource = endpoint_name

            add_span_arg_tags(
                span, endpoint_name, args, ARGS_NAME, TRACED_ARGS
            )

            region_name = deep_getattr(instance, "meta.region_name")

            meta = {
                "aws.agent": "botocore",
                "aws.operation": operation,
                "aws.region": region_name,
            }
            for key, value in meta.items():
                span.set_attribute(key, value)

            result = original_func(*args, **kwargs)

            span.set_attribute(
                "http.status_code",
                result["ResponseMetadata"]["HTTPStatusCode"],
            )
            span.set_attribute(
                "retry_attempts", result["ResponseMetadata"]["RetryAttempts"],
            )

            return result


def unwrap(obj, attr):
    function = getattr(obj, attr, None)
    if (
        function
        and isinstance(function, ObjectProxy)
        and hasattr(function, "__wrapped__")
    ):
        setattr(obj, attr, function.__wrapped__)


def add_span_arg_tags(span, endpoint_name, args, args_names, args_traced):
    def truncate_arg_value(value, max_len=1024):
        """Truncate values which are bytes and greater than `max_len`.
        Useful for parameters like "Body" in `put_object` operations.
        """
        if isinstance(value, bytes) and len(value) > max_len:
            return b"..."

        return value

    if endpoint_name not in ["kms", "sts"]:
        tags = dict(
            (name, value)
            for (name, value) in zip(args_names, args)
            if name in args_traced
        )
        tags = flatten_dict(tags)
        for key, value in {
            k: truncate_arg_value(v)
            for k, v in tags.items()
            if k not in {"s3": ["params.Body"]}.get(endpoint_name, [])
        }.items():
            span.set_attribute(key, value)


def flatten_dict(dict_, sep=".", prefix=""):
    """
    Returns a normalized dict of depth 1 with keys in order of embedding
    """
    # adapted from https://stackoverflow.com/a/19647596
    return (
        {
            prefix + sep + k if prefix else k: v
            for kk, vv in dict_.items()
            for k, v in flatten_dict(vv, sep, kk).items()
        }
        if isinstance(dict_, dict)
        else {prefix: dict_}
    )


def deep_getattr(obj, attr_string, default=None):
    """
    Returns the attribute of `obj` at the dotted path given by `attr_string`
    If no such attribute is reachable, returns `default`

    >>> deep_getattr(cass, "cluster")
    <cassandra.cluster.Cluster object at 0xa20c350

    >>> deep_getattr(cass, "cluster.metadata.partitioner")
    u"org.apache.cassandra.dht.Murmur3Partitioner"

    >>> deep_getattr(cass, "i.dont.exist", default="default")
    "default"
    """
    attrs = attr_string.split(".")
    for attr in attrs:
        try:
            obj = getattr(obj, attr)
        except AttributeError:
            return default

    return obj
