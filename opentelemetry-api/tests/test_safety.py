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
# type: ignore

from abc import ABC, abstractmethod
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from opentelemetry.safety import BaseSafety, safety


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
    # pylint: disable=no-self-use
    def get_tracer(self, instrumenting_module_name: str) -> Tracer:
        return NoOpTracer()


# Would be defined in the SDK
class SDKSpan(BaseSafety, Span):
    @safety(None)
    def update_name(self, name: str) -> None:
        print(f"Name has been updated to {name}")

    def _init(self, *args, **kwargs):
        pass

    def _get_no_op_class(self):
        return NoOpSpan


# Would be defined in the SDK
class SDKTracer(BaseSafety, Tracer):
    @safety(NoOpSpan())
    def start_span(self, name: str) -> Span:
        return SDKSpan.__new__(SDKSpan, _allow_instantiation=True)

    def _init(self, *args, **kwargs):
        pass

    def _get_no_op_class(self):
        return NoOpTracer


# Would be defined in the SDK
class SDKTracerProvider(BaseSafety, TracerProvider):
    @safety(NoOpTracer())
    def get_tracer(self, instrumenting_module_name: str) -> Tracer:
        return SDKTracer.__new__(SDKTracer, _allow_instantiation=True)

    def _init(self, *args, **kwargs):
        pass

    def _get_no_op_class(self):
        return NoOpTracerProvider


# Would be defined in the API
@safety(NoOpTracerProvider())
def get_tracer_provider() -> TracerProvider:
    # SDKTracerProvider would be loaded by entry points.
    return SDKTracerProvider.__new__(
        SDKTracerProvider, _allow_instantiation=True
    )


class TestSafety(TestCase):
    def test_no_direct_instantiation(self):
        with self.assertWarns(UserWarning):
            self.assertIsInstance(SDKSpan(), NoOpSpan)

        with self.assertWarns(UserWarning):
            self.assertIsInstance(SDKTracer(), NoOpTracer)

        with self.assertWarns(UserWarning):
            self.assertIsInstance(SDKTracerProvider(), NoOpTracerProvider)

    def test_indirect_instantiation(self):
        with self.assertRaises(AssertionError):
            with self.assertWarns(UserWarning):
                sdk_tracer_provider = get_tracer_provider()
                self.assertIsInstance(sdk_tracer_provider, SDKTracerProvider)

        with self.assertRaises(AssertionError):
            with self.assertWarns(UserWarning):
                sdk_tracer = sdk_tracer_provider.get_tracer(
                    "instrumenting_module_name"
                )
                self.assertIsInstance(sdk_tracer, SDKTracer)

        with self.assertRaises(AssertionError):
            with self.assertWarns(UserWarning):
                sdk_span = sdk_tracer.start_span("name")
                self.assertIsInstance(sdk_span, SDKSpan)

        with patch("sys.stdout", new=StringIO()) as patched_stdout:
            sdk_span.update_name("name")
            with self.assertRaises(AssertionError):
                with self.assertWarns(UserWarning):
                    self.assertEqual(
                        patched_stdout.getvalue(),
                        "Name has been updated to name",
                    )

    def test_wrong_arguments(self):
        with self.assertWarns(UserWarning):
            self.assertIsInstance(
                # pylint: disable=too-many-function-args
                get_tracer_provider("wrong_argument"),
                NoOpTracerProvider,
            )

        sdk_tracer_provider = get_tracer_provider()

        # pylint: disable=no-value-for-parameter
        with self.assertWarns(UserWarning):
            self.assertIsInstance(sdk_tracer_provider.get_tracer(), NoOpTracer)

        sdk_tracer = sdk_tracer_provider.get_tracer(
            "instrumenting_module_name"
        )

        with self.assertWarns(UserWarning):
            self.assertIsInstance(sdk_tracer.start_span(), NoOpSpan)

        sdk_span = sdk_tracer.start_span("name")

        with self.assertWarns(UserWarning):
            self.assertIs(sdk_span.update_name(), None)
