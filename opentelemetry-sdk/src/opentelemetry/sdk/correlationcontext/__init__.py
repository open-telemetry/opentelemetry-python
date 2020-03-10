# Copyright 2020, OpenTelemetry Authors
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

import typing

from opentelemetry import correlationcontext as cctx_api
from opentelemetry.context import get_value, set_value
from opentelemetry.context.context import Context


class CorrelationContext(cctx_api.CorrelationContext):
    def get_correlations(self, context: typing.Optional[Context] = None):
        correlations = get_value(
            cctx_api.CORRELATION_CONTEXT_KEY, context=context
        )
        if correlations:
            return correlations
        return {}

    def get_correlation(
        self, name, context: typing.Optional[Context] = None
    ) -> typing.Optional[object]:
        correlations = get_value(
            cctx_api.CORRELATION_CONTEXT_KEY, context=context
        )
        if correlations:
            return correlations.get(name)
        return None

    def set_correlation(
        self, name, value, context: typing.Optional[Context] = None
    ) -> Context:
        correlations = get_value(
            cctx_api.CORRELATION_CONTEXT_KEY, context=context
        )
        if correlations:
            correlations[name] = value
        else:
            correlations = {name: value}
        return set_value(
            cctx_api.CORRELATION_CONTEXT_KEY, correlations, context=context
        )

    def remove_correlation(
        self, name, context: typing.Optional[Context] = None
    ) -> Context:
        correlations = get_value(
            cctx_api.CORRELATION_CONTEXT_KEY, context=context
        )
        if correlations and name in correlations:
            del correlations[name]

        return set_value(
            cctx_api.CORRELATION_CONTEXT_KEY, correlations, context=context
        )

    def clear_correlations(
        self, context: typing.Optional[Context] = None
    ) -> Context:
        return set_value(cctx_api.CORRELATION_CONTEXT_KEY, {}, context=context)
