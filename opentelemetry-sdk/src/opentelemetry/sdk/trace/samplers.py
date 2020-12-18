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

from logging import getLogger
from typing import Callable

from opentelemetry.configuration import Configuration
from opentelemetry.sdk.trace import sampling

_logger = getLogger(__name__)


class _Samplers:

    registry = {}

    @classmethod
    def register(cls, name: str) -> Callable:
        def _wrapper(wrapped_class: sampling.Sampler) -> Callable:
            cls.registry[name] = wrapped_class
            return wrapped_class

        return _wrapper

    @classmethod
    def get_sampler(cls, name: str, **kwargs) -> sampling.Sampler:
        if name not in cls.registry:
            _logger.warning("Couldn't find sampler %s", name)
            return None
        klass = cls.registry[name]
        return klass(**kwargs)


@_Samplers.register("always_on")
class _AlwaysOnSampler(sampling.StaticSampler):
    def __init__(self):
        super().__init__(decision=sampling.Decision.RECORD_AND_SAMPLE)


@_Samplers.register("always_off")
class _AlwaysOffSampler(sampling.StaticSampler):
    def __init__(self):
        super().__init__(decision=sampling.Decision.DROP)


@_Samplers.register("traceidratio")
class _TraceIdRatioBasedSampler(sampling.TraceIdRatioBased):
    def __init__(self, rate: float):
        super().__init__(rate=rate)


@_Samplers.register("parentbased_always_on")
class _ParentBasedAlwaysOnSampler(sampling.ParentBased):
    def __init__(self):
        super().__init__(root=sampling.ALWAYS_ON)


@_Samplers.register("parentbased_always_off")
class _ParentBasedAlwaysOffSampler(sampling.ParentBased):
    def __init__(self):
        super().__init__(root=sampling.ALWAYS_OFF)


@_Samplers.register("parentbased_traceidratio")
class _ParentBasedTraceIdRatioSampler(sampling.ParentBased):
    def __init__(self, rate: float):
        root = sampling.TraceIdRatioBased(rate=rate)
        super().__init__(root=root)


def _get_from_env_or_default() -> sampling.Sampler:
    trace_sampler = (
        Configuration().get("TRACE_SAMPLER", "parentbased_always_on").lower()
    )
    kwargs = {}
    if trace_sampler in ["traceidratio", "parentbased_traceidratio"]:
        rate = Configuration().get("TRACE_SAMPLER_ARG", 1.0)
        kwargs["rate"] = float(rate)

    return _Samplers.get_sampler(trace_sampler, **kwargs)
