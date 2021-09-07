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

import os
import typing

import opentelemetry
from opentelemetry.context.context import Context
from opentelemetry.propagators.b3 import (B3SingleFormat, B3MultiFormat)
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.propagators import textmap
from opentelemetry.propagators.textmap import (
    DefaultGetter,
    DefaultSetter,
    Getter,
    Setter,
    TextMapPropagator,
    CarrierT,
    CarrierValT
)

class CompositeEnvPropagator(TextMapPropagator):
    def __init__(self, propagators : typing.Sequence[TextMapPropagator]):
        self._propagators = propagators

    def extract(self, carrier: CarrierT, context: typing.Optional[Context] = None, getter: Getter = DefaultGetter()) -> Context:
        if not self._propagators:
            self._propagators = [TraceContextTextMapPropagator(), W3CBaggagePropagator()]

        for propagator in self._propagators:
            if isinstance(propagator, B3SingleFormat):
                context = B3MultiFormat().extract(carrier, context, getter)
            else:
                context = propagator.extract(carrier, context, getter)
        return context

    def inject(self, carrier: CarrierT, context: typing.Optional[Context] = None, setter: Setter = textmap.default_setter) -> None:
        if not self._propagators:
            self._propagators = [TraceContextTextMapPropagator(), W3CBaggagePropagator()]

        for propagator in self._propagators:
            propagator.inject(carrier, context, setter)

    # function for the user to inject trace details or baggage
    def inject_to_carrier(self, context: typing.Optional[Context] = None):
        env_dict = os.environ.copy()
        self.inject(carrier=env_dict, context = context, setter = textmap.default_setter)
        return env_dict

    # function for the user to extract context
    def extract_context(self) -> Context:
        return self.extract(carrier=os.environ, getter = DefaultGetter())

    @property
    def fields(self) -> typing.Set[str]:
        # Returns a set with the fields set in `inject`.
        composite_fields = set()

        for propagator in self._propagators:
            for field in propagator.fields:
                composite_fields.add(field)

        return composite_fields
