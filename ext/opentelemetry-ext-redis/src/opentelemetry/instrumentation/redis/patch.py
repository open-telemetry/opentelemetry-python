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
#
# pylint:disable=relative-beyond-top-level
import redis
from wrapt import ObjectProxy, wrap_function_wrapper

from .util import _extract_conn_attributes, _format_command_args
from .version import __version__

_DEFAULT_SERVICE = "redis"
_RAWCMD = "db.statement"
_CMD = "redis.command"


def _patch(tracer_provider):
    """Patch the instrumented methods

    This duplicated doesn't look nice. The nicer alternative is to use an ObjectProxy on top
    of Redis and StrictRedis. However, it means that any "import redis.Redis" won't be instrumented.
    """
    setattr(
        redis,
        "_opentelemetry_tracer",
        tracer_provider.get_tracer(_DEFAULT_SERVICE, __version__),
    )

    if redis.VERSION < (3, 0, 0):
        wrap_function_wrapper(
            "redis", "StrictRedis.execute_command", traced_execute_command
        )
        wrap_function_wrapper(
            "redis.client", "BasePipeline.execute", traced_execute_pipeline
        )
        wrap_function_wrapper(
            "redis.client",
            "BasePipeline.immediate_execute_command",
            traced_execute_command,
        )
    else:
        wrap_function_wrapper(
            "redis", "Redis.execute_command", traced_execute_command
        )
        wrap_function_wrapper(
            "redis.client", "Pipeline.execute", traced_execute_pipeline
        )
        wrap_function_wrapper(
            "redis.client",
            "Pipeline.immediate_execute_command",
            traced_execute_command,
        )


def _unwrap(obj, attr):
    func = getattr(obj, attr, None)
    if isinstance(func, ObjectProxy) and hasattr(func, "__wrapped__"):
        setattr(obj, attr, func.__wrapped__)


def _unpatch():
    if redis.VERSION < (3, 0, 0):
        _unwrap(redis.StrictRedis, "execute_command")
        _unwrap(redis.StrictRedis, "pipeline")
        _unwrap(redis.Redis, "pipeline")
        _unwrap(
            redis.client.BasePipeline, "execute",  # pylint:disable=no-member
        )
        _unwrap(
            redis.client.BasePipeline,  # pylint:disable=no-member
            "immediate_execute_command",
        )
    else:
        _unwrap(redis.Redis, "execute_command")
        _unwrap(redis.Redis, "pipeline")
        _unwrap(redis.client.Pipeline, "execute")
        _unwrap(redis.client.Pipeline, "immediate_execute_command")


def traced_execute_command(func, instance, args, kwargs):
    tracer = getattr(redis, "_opentelemetry_tracer")
    query = _format_command_args(args)
    with tracer.start_as_current_span(_CMD) as span:
        span.set_attribute("service", tracer.instrumentation_info.name)
        span.set_attribute(_RAWCMD, query)
        _set_connection_attributes(span, instance)
        span.set_attribute("redis.args_length", len(args))
        return func(*args, **kwargs)


def traced_execute_pipeline(func, instance, args, kwargs):
    tracer = getattr(redis, "_opentelemetry_tracer")

    cmds = [_format_command_args(c) for c, _ in instance.command_stack]
    resource = "\n".join(cmds)

    with tracer.start_as_current_span(_CMD) as span:
        span.set_attribute("service", tracer.instrumentation_info.name)
        span.set_attribute(_RAWCMD, resource)
        _set_connection_attributes(span, instance)
        span.set_attribute(
            "redis.pipeline_length", len(instance.command_stack)
        )
        return func(*args, **kwargs)


def _set_connection_attributes(span, conn):
    for key, value in _extract_conn_attributes(
        conn.connection_pool.connection_kwargs
    ).items():
        span.set_attribute(key, value)
