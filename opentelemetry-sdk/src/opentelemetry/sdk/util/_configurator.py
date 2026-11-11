# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
from collections.abc import Sequence
from typing import Generic, TypeVar

from opentelemetry.sdk.util.instrumentation import (
    InstrumentationScope,
    _InstrumentationScopePredicateT,
)

ConfigT = TypeVar("ConfigT")
ConfiguratorRulesT = Sequence[tuple[_InstrumentationScopePredicateT, ConfigT]]


class RuleBasedConfigurator(Generic[ConfigT]):
    """Maps an instrumentation scope onto a configuration value.

    Args:
        rules: The ordered pairs of a predicate over an
            ``InstrumentationScope`` and the configuration to use when that
            predicate accepts. An empty sequence means every scope gets
            ``default_config``.
        default_config: The configuration returned when no predicate
            accepts.
    """

    def __init__(self, *, rules: ConfiguratorRulesT, default_config: ConfigT):
        self._rules = rules
        self._default_config = default_config

    def __call__(self, scope: InstrumentationScope) -> ConfigT:
        for predicate, config in self._rules:
            if predicate(scope):
                return config
        # by default return default config
        return self._default_config

    def update_rules(self, rules: ConfiguratorRulesT) -> None:
        """Replace the whole rule sequence.

        Args:
            rules: The new ordered pairs of predicate and configuration. The
                default configuration is left as it was.
        """
        self._rules = rules
