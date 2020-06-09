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
The opentelemetry-instrumentation-starlette package provides an ASGI middleware that can be used
on any ASGI framework (such as Django-channels / Quart) to track requests
timing through OpenTelemetry.
"""

from opentelemetry.ext.asgi import OpenTelemetryMiddleware
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.instrumentation.starlette.version import __version__  # noqa
from starlette import applications
from starlette.middleware import Middleware
from starlette.routing import Match


class StarletteInstrumentor(BaseInstrumentor):
    """An instrumentor for starlette

    See `BaseInstrumentor`
    """

    @staticmethod
    def instrument_app(app: applications.Starlette):
        """Instrument a previously instrumented Starlette application.
        """
        if not getattr(app, "_is_instrumented_by_opentelemetry", False):
            app.add_middleware(
                OpenTelemetryMiddleware, name_callback=_get_route_name
            )
            app._is_instrumented_by_opentelemetry = True

    def _instrument(self, **kwargs):
        self._original_starlette = applications.Starlette
        applications.Starlette = _InstrumentedStarlette

    def _uninstrument(self, **kwargs):
        applications.Starlette = self._original_starlette


class _InstrumentedStarlette(applications.Starlette):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_middleware(
            OpenTelemetryMiddleware, name_callback=_get_route_name
        )


def _get_route_name(scope):
    """Callback to retrieve the starlette route being served.
    """
    app = scope["app"]
    for route in app.routes:
        match, _ = route.matches(scope)
        if match == Match.FULL:
            return route.path
    # method only exists for http, if websocket
    # leave it blank.
    return scope.get("method", "")
