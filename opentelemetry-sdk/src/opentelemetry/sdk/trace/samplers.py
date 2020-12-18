from logging import getLogger
from typing import Callable

from opentelemetry.configuration import Configuration
from opentelemetry.sdk.trace import sampling

_logger = getLogger(__name__)


class Samplers:

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


@Samplers.register("always_on")
class AlwaysOnSampler(sampling.StaticSampler):
    def __init__(self):
        super().__init__(decision=sampling.Decision.RECORD_AND_SAMPLE)


@Samplers.register("always_off")
class AlwaysOffSampler(sampling.StaticSampler):
    def __init__(self):
        super().__init__(decision=sampling.Decision.DROP)


@Samplers.register("traceidratio")
class TraceIdRatioBasedSampler(sampling.TraceIdRatioBased):
    def __init__(self, rate: float):
        super().__init__(rate=rate)


@Samplers.register("parentbased_always_on")
class ParentBasedAlwaysOnSampler(sampling.ParentBased):
    def __init__(self):
        super().__init__(root=sampling.ALWAYS_ON)


@Samplers.register("parentbased_always_off")
class ParentBasedAlwaysOffSampler(sampling.ParentBased):
    def __init__(self):
        super().__init__(root=sampling.ALWAYS_OFF)


@Samplers.register("parentbased_traceidratio")
class ParentBasedTraceIdRatioSampler(sampling.ParentBased):
    def __init__(self, rate: float):
        root = sampling.TraceIdRatioBased(rate=rate)
        super().__init__(root=root)


def get_from_env_or_default() -> sampling.Sampler:
    trace_sampler = (
        Configuration().get("TRACE_SAMPLER", "parentbased_always_on").lower()
    )
    kwargs = {}
    if trace_sampler in ["traceidratio", "parentbased_traceidratio"]:
        rate = Configuration().get("TRACE_SAMPLER_ARG", 1.0)
        kwargs["rate"] = float(rate)

    return Samplers.get_sampler(trace_sampler, **kwargs)
