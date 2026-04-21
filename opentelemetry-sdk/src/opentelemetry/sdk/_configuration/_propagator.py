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

from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.propagators.textmap import TextMapPropagator
from opentelemetry.sdk._configuration._exceptions import ConfigurationError
from opentelemetry.sdk._configuration.models import (
    Propagator as PropagatorConfig,
)
from opentelemetry.sdk._configuration.models import (
    TextMapPropagator as TextMapPropagatorConfig,
)
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
)
from opentelemetry.util._importlib_metadata import entry_points


def _load_entry_point_propagator(name: str) -> TextMapPropagator:
    """Load a propagator by name from the opentelemetry_propagator entry point group."""
    try:
        ep = next(
            iter(entry_points(group="opentelemetry_propagator", name=name)),
            None,
        )
        if not ep:
            raise ConfigurationError(
                f"Propagator '{name}' not found. "
                "It may not be installed or may be misspelled."
            )
        return ep.load()()
    except ConfigurationError:
        raise
    except Exception as exc:
        raise ConfigurationError(
            f"Failed to load propagator '{name}': {exc}"
        ) from exc


def _propagators_from_textmap_config(
    config: TextMapPropagatorConfig,
) -> list[TextMapPropagator]:
    """Resolve a single TextMapPropagator config entry to a list of propagators."""
    result: list[TextMapPropagator] = []
    if config.tracecontext is not None:
        result.append(TraceContextTextMapPropagator())
    if config.baggage is not None:
        result.append(W3CBaggagePropagator())
    if config.b3 is not None:
        result.append(_load_entry_point_propagator("b3"))
    if config.b3multi is not None:
        result.append(_load_entry_point_propagator("b3multi"))
    return result


def create_propagator(
    config: PropagatorConfig | None,
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
            propagator = _load_entry_point_propagator(name)
            propagators.setdefault(type(propagator), propagator)

    return CompositePropagator(list(propagators.values()))


def configure_propagator(config: PropagatorConfig | None) -> None:
    """Configure the global text map propagator from declarative config.

    Always calls set_global_textmap to override any defaults (including the
    env-var-based tracecontext+baggage default set by the SDK).

    Args:
        config: Propagator config from the parsed config file, or None.
    """
    set_global_textmap(create_propagator(config))
