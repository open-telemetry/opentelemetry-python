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

# pylint: disable=too-many-lines

from enum import Enum


ASPNETCORE_DIAGNOSTICS_EXCEPTION_RESULT = "aspnetcore.diagnostics.exception.result"
"""
ASP.NET Core exception middleware handling result.
"""


ASPNETCORE_DIAGNOSTICS_HANDLER_TYPE = "aspnetcore.diagnostics.handler.type"
"""
Full type name of the [`IExceptionHandler`](https://learn.microsoft.com/dotnet/api/microsoft.aspnetcore.diagnostics.iexceptionhandler) implementation that handled the exception.
"""


ASPNETCORE_RATE_LIMITING_POLICY = "aspnetcore.rate_limiting.policy"
"""
Rate limiting policy name.
"""


ASPNETCORE_RATE_LIMITING_RESULT = "aspnetcore.rate_limiting.result"
"""
Rate-limiting result, shows whether the lease was acquired or contains a rejection reason.
"""


ASPNETCORE_REQUEST_IS_UNHANDLED = "aspnetcore.request.is_unhandled"
"""
Flag indicating if request was handled by the application pipeline.
"""


ASPNETCORE_ROUTING_IS_FALLBACK = "aspnetcore.routing.is_fallback"
"""
A value that indicates whether the matched route is a fallback route.
"""


ASPNETCORE_ROUTING_MATCH_STATUS = "aspnetcore.routing.match_status"
"""
Match result - success or failure.
"""

class AspnetcoreDiagnosticsExceptionResultValues(Enum):
    HANDLED = "handled"
    """Exception was handled by the exception handling middleware."""

    UNHANDLED = "unhandled"
    """Exception was not handled by the exception handling middleware."""

    SKIPPED = "skipped"
    """Exception handling was skipped because the response had started."""

    ABORTED = "aborted"
    """Exception handling didn't run because the request was aborted."""
class AspnetcoreRateLimitingResultValues(Enum):
    ACQUIRED = "acquired"
    """Lease was acquired."""

    ENDPOINT_LIMITER = "endpoint_limiter"
    """Lease request was rejected by the endpoint limiter."""

    GLOBAL_LIMITER = "global_limiter"
    """Lease request was rejected by the global limiter."""

    REQUEST_CANCELED = "request_canceled"
    """Lease request was canceled."""
class AspnetcoreRoutingMatchStatusValues(Enum):
    SUCCESS = "success"
    """Match succeeded."""

    FAILURE = "failure"
    """Match failed."""
