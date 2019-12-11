# Copyright 2019, OpenTelemetry Authors
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

from opentelemetry.context import Context
from opentelemetry.context.propagation import Carrier, Getter, Setter


class ContextKeys:
    """ TODO """

    KEY = "baggage"

    @classmethod
    def span_context_key(cls):
        """ TODO """
        return cls.KEY


class HTTPExtractor:
    """The default HTTPExtractor.

    Used when no HTTPExtractor implementation is available.
    """

    def extract(
        self, ctx: Context, carrier: Carrier, getter: Getter
    ) -> Context:
        """ TODO """
        # pylint: disable=unused-argument
        return ctx


class HTTPInjector:
    """The default HTTPInjector.

    Used when no HTTPInjector implementation is available.
    """

    def inject(
        self, ctx: Context, carrier: Carrier, setter: Setter
    ) -> Context:
        """ TODO """
        # pylint: disable=unused-argument
        return ctx
