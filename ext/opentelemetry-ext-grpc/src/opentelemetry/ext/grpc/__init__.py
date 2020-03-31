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


def client_interceptor(tracer):
    """Create a gRPC client channel interceptor.

    Args:
        tracer: The tracer to use to create client-side spans.

    Returns:
        An invocation-side interceptor object.
    """
    from . import _client

    return _client.OpenTelemetryClientInterceptor(tracer)


def server_interceptor(tracer):
    """Create a gRPC server interceptor.

    Args:
        tracer: The tracer to use to create server-side spans.

    Returns:
        A service-side interceptor object.
    """
    from . import _server

    return _server.OpenTelemetryServerInterceptor(tracer)
