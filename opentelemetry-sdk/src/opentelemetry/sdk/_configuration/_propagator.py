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

from __future__ import annotations

from typing import Optional

from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.propagators.textmap import TextMapPropagator
from opentelemetry.sdk._configuration._common import load_entry_point
from opentelemetry.sdk._configuration.models import (
    Propagator as PropagatorConfig,
)
from opentelemetry.sdk._configuration.models import (
    TextMapPropagator as TextMapPropagatorConfig,
)
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
)

# Propagators bundled with the SDK — no entry point lookup needed.
_PROPAGATOR_REGISTRY: dict = {
    "tracecontext": lambda _: TraceContextTextMapPropagator(),
    "baggage": lambda _: W3CBaggagePropagator(),
}


def _propagators_from_textmap_config(
    config: TextMapPropagatorConfig,
) -> list[TextMapPropagator]:
    """Resolve a TextMapPropagator config to a list of propagators.

    Known names (tracecontext, baggage) are bootstrapped directly via
    _PROPAGATOR_REGISTRY. Known schema fields not in the registry (b3, b3multi)
    and unknown plugin names from additional_properties are loaded via the
    ``opentelemetry_propagator`` entry point group.
    """
    result: list[TextMapPropagator] = []
    for name in _PROPAGATOR_REGISTRY:
        if getattr(config, name, None) is not None:
            result.append(_PROPAGATOR_REGISTRY[name](getattr(config, name)))

    # Known schema fields not in registry (b3, b3multi) — loaded via entry point
    for name in ("b3", "b3multi"):
        if getattr(config, name, None) is not None:
            result.append(load_entry_point("opentelemetry_propagator", name)())

    # Plugin propagators from additional_properties
    for name in config.additional_properties:
        result.append(load_entry_point("opentelemetry_propagator", name)())

    return result


def create_propagator(
    config: Optional[PropagatorConfig],
) -> CompositePropagator:
    """Create a CompositePropagator from declarative config.

    If config is None or has no propagators defined, returns an empty
    CompositePropagator (no-op), ensuring "what you see is what you get"
    semantics — the env-var-based default propagators are not used.

    Args:
        config: Propagator config from the parsed config file, or None.

    Returns:
        A CompositePropagator wrapping all configured propagators.
    """
    if config is None:
        return CompositePropagator([])

    propagators: dict[type[TextMapPropagator], TextMapPropagator] = {}

    # Process structured composite list
    if config.composite:
        for entry in config.composite:
            for propagator in _propagators_from_textmap_config(entry):
                propagators.setdefault(type(propagator), propagator)

    # Process composite_list (comma-separated propagator names via entry_points)
    if config.composite_list:
        for name in config.composite_list.split(","):
            name = name.strip()
            if not name or name.lower() == "none":
                continue
            propagator = load_entry_point("opentelemetry_propagator", name)()
            propagators.setdefault(type(propagator), propagator)

    return CompositePropagator(list(propagators.values()))


def configure_propagator(config: Optional[PropagatorConfig]) -> None:
    """Configure the global text map propagator from declarative config.

    Always calls set_global_textmap to override any defaults (including the
    env-var-based tracecontext+baggage default set by the SDK).

    Args:
        config: Propagator config from the parsed config file, or None.
    """
    set_global_textmap(create_propagator(config))
