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



# pylint:disable=no-name-in-module
# pylint:disable=relative-beyond-top-level
from contextlib import contextmanager

from wrapt import wrap_function_wrapper as _wrap

# pylint:disable=import-outside-toplevel
# pylint:disable=import-self
from opentelemetry import trace
from opentelemetry.auto_instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.ext.grpc.grpcext import intercept_channel, intercept_server
from opentelemetry.ext.grpc.version import __version__
from opentelemetry.instrumentation.utils import unwrap


class GrpcInstrumentorServer(BaseInstrumentor):
    def __init__(self):
        self.server = None

    def _instrument(self, **kwargs):
        _wrap("grpc", "server", self.wrapper_fn)

    def _uninstrument(self, **kwargs):
        unwrap("grpc", "server")

    def wrapper_fn(self, original_func, instance, args, kwargs):
        self.server = original_func(*args, **kwargs)
        self.server = intercept_server(self.server, server_interceptor())


class GrpcInstrumentorClient(BaseInstrumentor):
    def __init__(self):
        self.channel = None

    def _instrument(self, **kwargs):

        if kwargs.get("channel_type") == "secure":
            _wrap("grpc", "secure_channel", self.wrapper_fn)

        else:
            _wrap("grpc", "insecure_channel", self.wrapper_fn)

    def _uninstrument(self, **kwargs):
        if kwargs.get("channel_type") == "secure":
            unwrap("grpc", "secure_channel")

        else:
            unwrap("grpc", "insecure_channel")

    @contextmanager
    def wrapper_fn(self, original_func, instance, args, kwargs):
        with original_func(*args, **kwargs) as channel:
            self.channel = intercept_channel(channel, client_interceptor())
            yield self.channel


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
