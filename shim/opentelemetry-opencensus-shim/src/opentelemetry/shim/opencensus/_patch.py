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

from functools import lru_cache
from logging import getLogger
from typing import Optional

from opencensus.trace.span_context import SpanContext
from opencensus.trace.tracer import Tracer
from opencensus.trace.tracers.noop_tracer import NoopTracer

from opentelemetry import trace
from opentelemetry.shim.opencensus._shim_tracer import ShimTracer
from opentelemetry.shim.opencensus.version import __version__

_logger = getLogger(__name__)


def install_shim(
    tracer_provider: Optional[trace.TracerProvider] = None,
) -> None:
    otel_tracer = trace.get_tracer(
        "opentelemetry-opencensus-shim",
        __version__,
        tracer_provider=tracer_provider,
    )

    @lru_cache()
    def cached_shim_tracer(span_context: SpanContext) -> ShimTracer:
        return ShimTracer(
            NoopTracer(),
            oc_span_context=span_context,
            otel_tracer=otel_tracer,
        )

    def fget_tracer(self: Tracer) -> ShimTracer:
        # self.span_context is how instrumentations pass propagated context into OpenCensus e.g.
        # https://github.com/census-instrumentation/opencensus-python/blob/fd064f438c5e490d25b004ee2545be55d2e28679/contrib/opencensus-ext-flask/opencensus/ext/flask/flask_middleware.py#L147-L153
        return cached_shim_tracer(self.span_context)

    def fset_tracer(self, value) -> None:
        # ignore attempts to set the value
        pass

    # Tracer's constructor sets self.tracer to either a NoopTracer or ContextTracer depending
    # on sampler:
    # https://github.com/census-instrumentation/opencensus-python/blob/2e08df591b507612b3968be8c2538dedbf8fab37/opencensus/trace/tracer.py#L63.
    # We monkeypatch Tracer.tracer with a property to return a shim instance instead. This
    # makes all instances of Tracer (even those already created) use a ShimTracer.
    Tracer.tracer = property(fget_tracer, fset_tracer)
    _logger.info("Installed OpenCensus shim")


def uninstall_shim() -> None:
    if hasattr(Tracer, "tracer"):
        del Tracer.tracer
