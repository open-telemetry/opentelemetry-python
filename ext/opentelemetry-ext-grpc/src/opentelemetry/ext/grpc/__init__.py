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
from contextlib import contextmanager

import grpc
from concurrent import futures
from opentelemetry import trace
from opentelemetry.ext.grpc.version import __version__
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.auto_instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import get_tracer
from wrapt import ObjectProxy
from wrapt import wrap_function_wrapper as _wrap
from opentelemetry.ext.grpc.grpcext import intercept_channel, intercept_server

import pdb
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleExportSpanProcessor,
)


class GrpcInstrumentorServer(BaseInstrumentor):
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer_provider()
    server = None

    def _instrument(self, **kwargs):
        self.server = grpc.server(futures.ThreadPoolExecutor())
        self.server = intercept_server(self.server, server_interceptor())

    def _uninstrument(self, **kwargs):
        if hasattr(self.server, 'stop'):
            return self.server.stop(kwargs.get('grace'))


class GrpcInstrumentorClient(BaseInstrumentor):
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer_provider()
    channel = None

    def _instrument(self, **kwargs):
        hostport = kwargs.get('hostport')

        if kwargs.get('channel_type') == 'secure':
            self.channel = secure_channel_wrapper(hostport, kwargs.get("credentials"))

        else:
            self.channel = insecure_channel_wrapper(hostport)

    def _uninstrument(self, **kwargs):

        if hasattr(self.channel, 'close'):
            return self.channel.close()


@contextmanager
def insecure_channel_wrapper(hostport):
    with grpc.insecure_channel(hostport) as channel:
        yield intercept_channel(channel, client_interceptor())


@contextmanager
def secure_channel_wrapper(hostport, credentials):
    with grpc.secure_channel(hostport, credentials) as channel:
        yield intercept_channel(channel, client_interceptor())


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
