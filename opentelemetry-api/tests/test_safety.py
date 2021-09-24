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

from unittest import TestCase
from abc import ABC, abstractmethod

from opentelemetry import BaseSafety, safety


# Would be defined in the API
class Span(ABC):
    @abstractmethod
    def update_name(self, name: str) -> None:
        pass


# Would be defined in the API
class NoOpSpan(Span):
    def update_name(self, name: str) -> None:
        pass


# Would be defined in the API
class Tracer(ABC):
    @abstractmethod
    def start_span(self, name: str) -> Span:
        pass


# Would be defined in the API
class NoOpTracer(Tracer):
    def start_span(self, name: str) -> Span:
        return NoOpSpan()


# Would be defined in the API
class TracerProvider(ABC):
    @abstractmethod
    def get_tracer(self, instrumenting_module_name: str) -> Tracer:
        pass


# Would be defined in the API
class NoOpTracerProvider:
    def get_tracer(self, instrumenting_module_name: str) -> Tracer:
        return NoOpTracer()


# Would be defined in the SDK
class SDKSpan(BaseSafety, Span):
    @safety(None)
    def update_name(self, name: str) -> None:
        print(f"Name has been updated to {name}")


# Would be defined in the SDK
class SDKTracer(Tracer):
    @safety(NoOpSpan())
    def start_span(self, name: str) -> Span:
        return SDKSpan.__new__(_allow_instantiation=True)


# Would be defined in the API
def get_tracer_provider() -> TracerProvider:
    # SDKTracerProvider would be loaded by entry points.
    return SDKTracerProvider.__new__(_allow_instantiation=True)


# Would be defined in the SDK
class SDKTracerProvider(TracerProvider):
    @safety(NoOpTracer())
    def get_tracer(self, instrumenting_module_name: str) -> Tracer:
        return SDKTracer.__new__(_allow_instantiation=True)


class TestSafety(TestCase):

    def test_safety(self):
        pass
