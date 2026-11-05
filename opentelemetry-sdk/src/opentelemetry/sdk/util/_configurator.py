# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
"""Selection of a per-scope configuration by the first matching rule.

The SDK lets a tracer, a meter or a logger be configured differently depending
on which instrumentation scope asked for it. ``RuleBasedConfigurator`` holds
the ordered rules that make that choice and is called once per scope, when the
tracer, the meter or the logger for that scope is first created.
"""

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

    The rules are tried in order and the first predicate that accepts the
    scope decides, so a narrower rule has to be placed before a broader one.

    Args:
        rules: The ordered pairs of a predicate over an
            ``InstrumentationScope`` and the configuration to use when that
            predicate accepts. An empty sequence means every scope gets
            ``default_config``.
        default_config: The configuration returned when no predicate
            accepts.
    """

    def __init__(self, *, rules: ConfiguratorRulesT, default_config: ConfigT):
        """Build the configurator.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders. Both are keyword only.
        """
        self._rules = rules
        self._default_config = default_config

    def __call__(self, scope: InstrumentationScope) -> ConfigT:
        """Return the configuration that applies to ``scope``.

        Args:
            scope: The instrumentation scope to configure.

        Returns:
            The configuration of the first rule whose predicate accepts
            ``scope``, or the default configuration when none does. The value
            is returned as it is rather than copied, so several scopes can
            share one configuration object.
        """
        for predicate, config in self._rules:
            if predicate(scope):
                return config
        # by default return default config
        return self._default_config

    def update_rules(self, rules: ConfiguratorRulesT) -> None:
        """Replace the whole rule sequence.

        A configuration already handed to a scope is not revisited, so the
        new rules only affect calls made after this one.

        Args:
            rules: The new ordered pairs of predicate and configuration. The
                default configuration is left as it was.
        """
        self._rules = rules
