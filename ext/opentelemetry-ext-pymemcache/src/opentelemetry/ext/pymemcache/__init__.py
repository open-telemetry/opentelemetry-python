
import logging

import pymemcache
from wrapt import ObjectProxy
from wrapt import wrap_function_wrapper as _wrap

from opentelemetry.auto_instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.ext.pymemcache.version import __version__
from opentelemetry.trace import SpanKind, get_tracer
from opentelemetry.trace.status import Status, StatusCanonicalCode

logger = logging.getLogger(__name__)

ATTRIBUTE_JINJA2_TEMPLATE_NAME = "jinja2.template_name"
ATTRIBUTE_JINJA2_TEMPLATE_PATH = "jinja2.template_path"
DEFAULT_TEMPLATE_NAME = "<memory>"
COMMANDS = ["set", "set_many", "add", "replace", "append",
    "prepend", "cas", "get", "get_many", "gets", "gets_many", 
    "delete", "delete_many", "incr", "decr", "touch", "stats",
    "version", "flush_all", "quit"
]

# def set_multi(self, *args, **kwargs):
#     """set_multi is an alias for set_many"""
#     return self._traced_cmd('set_many', *args, **kwargs)

# def get_multi(self, *args, **kwargs):
#     """set_multi is an alias for set_many"""
#     return self._traced_cmd('get_many', *args, **kwargs)

def _with_tracer_wrapper(func):
    """Helper for providing tracer for wrapper functions.
    """

    def _with_tracer(tracer):
        def wrapper(wrapped, instance, args, kwargs):
            return func(tracer, wrapped, instance, args, kwargs)

        return wrapper

    return _with_tracer


@_with_tracer_wrapper
def _wrap_cmd(tracer, wrapped, instance, args, kwargs):
    with tracer.start_as_current_span(
        "memcached.command", kind=SpanKind.INTERNAL, attributes={}
    ):
        print('did this work', *args, **kwargs)
        return wrapped(*args, **kwargs)


def _unwrap(obj, attr):
    func = getattr(obj, attr, None)
    if func and isinstance(func, ObjectProxy) and hasattr(func, "__wrapped__"):
        setattr(obj, attr, func.__wrapped__)


class PymemcacheInstrumentor(BaseInstrumentor):
    """An instrumentor for pymemcache
    See `BaseInstrumentor`
    """

    def _instrument(self, **kwargs):
        tracer_provider = kwargs.get("tracer_provider")
        tracer = get_tracer(__name__, __version__, tracer_provider)

        for command in COMMANDS: 
            # print(dir(pymemcache.client.base))
            
            _wrap("pymemcache.client.base", "Client.{}".format(command), _wrap_cmd(tracer))


    def _uninstrument(self, **kwargs):

        for command in COMMANDS:
            _unwrap(pymemcache.client, "{}".format(command))
