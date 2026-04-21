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
from collections.abc import Sequence
from typing import Generic, TypeVar

from opentelemetry.sdk.util.instrumentation import (
    InstrumentationScope,
    _InstrumentationScopePredicateT,
)

ConfigT = TypeVar("ConfigT")
ConfiguratorRulesT = Sequence[tuple[_InstrumentationScopePredicateT, ConfigT]]


class RuleBasedConfigurator(Generic[ConfigT]):
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
        self._rules = rules
