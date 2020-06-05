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

# pylint:disable=import-outside-toplevel
# pylint:disable=import-self
# pylint:disable=no-name-in-module
# pylint:disable=relative-beyond-top-level
import grpc
from opentelemetry import trace
from opentelemetry.ext.grpc.version import __version__
from opentelemetry.auto_instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import get_tracer
from wrapt import ObjectProxy
from wrapt import wrap_function_wrapper as _wrap

class GrpcInstrumentorServer (BaseInstrumentor):

    def _instrument(self, **kwargs):
        tracer = self.get_trace(kwargs)
        _wrap(grpc,'server', server_interceptor(tracer_provider = get_tracer_provider(kwargs)))
        _wrap(grpc, 'secure_channel',server_interceptor(tracer_provider= get_tracer_provider(kwargs)))

        

    def _uninstrument(self, **kwargs):
        _unwrap(grpc, 'server')
        


class GrpcInstrumeentorClient (BaseInstrumentor):

    def _instrument(self, **kwargs):
         tracer = self.get_trace(kwargs)
         _wrap(grpc,'insecure_channel', client_interceptor(tracer_provider = get_tracer_provider(kwargs)))
         _wrap(grpc, 'secure_channel',client_interceptor(tracer_provider= get_tracer_provider(kwargs)))


     

    def _uninstrument(self, **kwargs):

        _unwrap(grpc, 'secure_channel')
        _unwrap(grpc, 'insecure_channel')

def _unwrap(obj, attr):
    func = getattr(obj,attr, None)

    if func and isinstance(func, ObjectProxy) and hasattr(func,"__wrapped__"):
        setattr(obj,attr,func.__wrapped__)

def get_tracer_provider (**kwargs):
    return  kwargs.get("tracer_provider")


def client_interceptor(tracer_provider=None):
    """Create a gRPC client channel interceptor.

    Args:
        tracer: The tracer to use to create client-side spans.

    Returns:
        An invocation-side interceptor object.
    """
    from . import _client

    tracer = trace.get_tracer(__name__, __version__, tracer_provider)

    return _client.OpenTelemetryClientInterceptor(tracer)


def server_interceptor(tracer_provider=None):
    """Create a gRPC server interceptor.

    Args:
        tracer: The tracer to use to create server-side spans.

    Returns:
        A service-side interceptor object.
    """
    from . import _server

    tracer = trace.get_tracer(__name__, __version__, tracer_provider)

    return _server.OpenTelemetryServerInterceptor(tracer)
