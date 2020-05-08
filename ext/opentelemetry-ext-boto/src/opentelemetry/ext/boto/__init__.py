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

# Note: This package is not named "boto" because of
# https://github.com/PyCQA/pylint/issues/2648

"""
This library builds on the OpenTelemetry WSGI middleware to track web requests
in Boto applications. In addition to opentelemetry-ext-wsgi, it supports
boto-specific features such as:

* The Boto endpoint name is used as the Span name.
* The ``http.route`` Span attribute is set so that one can see which URL rule
  matched a request.

Usage
-----

.. code-block:: python

    # FIXME add example

API
---
"""

import logging

from boto.connection import AWSQueryConnection, AWSAuthConnection

from inspect import currentframe

from wrapt import wrap_function_wrapper, ObjectProxy

from opentelemetry.auto_instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import SpanKind, get_tracer
from opentelemetry.ext.boto.version import __version__

logger = logging.getLogger(__name__)

AWS_QUERY_ARGS_NAME = ("operation_name", "params", "path", "verb")
AWS_AUTH_ARGS_NAME = (
    "method",
    "path",
    "headers",
    "data",
    "host",
    "auth_path",
    "sender",
)
AWS_QUERY_TRACED_ARGS = ["operation_name", "params", "path"]
AWS_AUTH_TRACED_ARGS = ["path", "data", "host"]
BLACKLIST_ENDPOINT_TAGS = {
    "s3": ["params.Body"],
}
REGION = "aws.region"
AGENT = "aws.agent"
OPERATION = "aws.operation"


def _get_instance_region_name(instance):
    region = getattr(instance, "region", None)

    if not region:
        return None
    if isinstance(region, str):
        return region.split(":")[1]
    else:
        return region.name


class BotoInstrumentor(BaseInstrumentor):
    """A instrumentor for boto.Boto

    See `BaseInstrumentor`
    """

    def __init__(self):
        super().__init__()
        self._original_boto = None

    def _instrument(self, **kwargs):
        # AWSQueryConnection and AWSAuthConnection are two different classes
        # called by different services for connection.
        # For exemple EC2 uses AWSQueryConnection and S3 uses
        # AWSAuthConnection

        # FIXME should the tracer provider be accessed via Configuration
        # instead?
        self._tracer = get_tracer(
            __name__, __version__, kwargs.get("tracer_provider")
        )

        wrap_function_wrapper(
            "boto.connection",
            "AWSQueryConnection.make_request",
            self._patched_query_request
        )
        wrap_function_wrapper(
            "boto.connection",
            "AWSAuthConnection.make_request",
            self._patched_auth_request
        )

    def _uninstrument(self, **kwargs):
        unwrap(AWSQueryConnection, "make_request")
        unwrap(AWSAuthConnection, "make_request")

    def _patched_query_request(self, original_func, instance, args, kwargs):

        endpoint_name = getattr(instance, "host").split(".")[0]

        with self._tracer.start_as_current_span(
            "{}.command".format(endpoint_name),
            kind=SpanKind.CONSUMER,
        ) as span:
            operation_name = None
            if args:
                operation_name = args[0]
                span.resource = "{}.{}".format(
                    endpoint_name, operation_name.lower()
                )
            else:
                span.resource = endpoint_name

            add_span_arg_tags(
                span,
                endpoint_name,
                args,
                AWS_QUERY_ARGS_NAME,
                AWS_QUERY_TRACED_ARGS
            )

            # Obtaining region name
            region_name = _get_instance_region_name(instance)

            meta = {
                AGENT: "boto",
                OPERATION: operation_name,
            }
            if region_name:
                meta[REGION] = region_name

            for key, value in meta.items():
                span.set_attribute(key, value)

            # Original func returns a boto.connection.HTTPResponse object
            result = original_func(*args, **kwargs)
            span.set_attribute("http.status_code", getattr(result, "status"))
            span.set_attribute("http.method", getattr(result, "_method"))

            return result

    def _patched_auth_request(self, original_func, instance, args, kwargs):
        # Catching the name of the operation that called make_request()
        operation_name = None

        # Go up the stack until we get the first non-ddtrace module
        # DEV: For `lambda.list_functions()` this should be:
        #        - ddtrace.contrib.boto.patch
        #        - ddtrace.vendor.wrapt.wrappers
        #        - boto.awslambda.layer1 (make_request)
        #        - boto.awslambda.layer1 (list_functions)
        # But can vary depending on Python versions; that"s why we use an
        # heuristic
        frame = currentframe().f_back
        operation_name = None
        while frame:
            if frame.f_code.co_name == "make_request":
                operation_name = frame.f_back.f_code.co_name
                break
            frame = frame.f_back

        endpoint_name = getattr(instance, "host").split(".")[0]

        with self._tracer.start_as_current_span(
            "{}.command".format(endpoint_name),
            kind=SpanKind.CONSUMER,
        ) as span:
            if args:
                http_method = args[0]
                span.resource = "%s.%s" % (endpoint_name, http_method.lower())
            else:
                span.resource = endpoint_name

            add_span_arg_tags(
                span,
                endpoint_name,
                args,
                AWS_AUTH_ARGS_NAME,
                AWS_AUTH_TRACED_ARGS
            )

            # Obtaining region name
            region_name = _get_instance_region_name(instance)

            meta = {
                AGENT: "boto",
                OPERATION: operation_name,
            }
            if region_name:
                meta[REGION] = region_name

            for key, value in meta.items():
                span.set_attribute(key, value)

            # Original func returns a boto.connection.HTTPResponse object
            result = original_func(*args, **kwargs)
            span.set_attribute("http.status_code", getattr(result, "status"))
            span.set_attribute("http.method", getattr(result, "_method"))

            return result


def truncate_arg_value(value, max_len=1024):
    """Truncate values which are bytes and greater than `max_len`.
    Useful for parameters like "Body" in `put_object` operations.
    """
    if isinstance(value, bytes) and len(value) > max_len:
        return b"..."

    return value


def add_span_arg_tags(span, endpoint_name, args, args_names, args_traced):
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


def flatten_dict(d, sep=".", prefix=""):
    """
    Returns a normalized dict of depth 1 with keys in order of embedding
    """
    # adapted from https://stackoverflow.com/a/19647596
    return (
        {
            prefix + sep + k if prefix else k: v
            for kk, vv in d.items()
            for k, v in flatten_dict(vv, sep, kk).items()
        }
        if isinstance(d, dict)
        else {prefix: d}
    )


def unwrap(obj, attr):
    f = getattr(obj, attr, None)
    if f and isinstance(f, ObjectProxy) and hasattr(f, "__wrapped__"):
        setattr(obj, attr, f.__wrapped__)
