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
#

import typing

import opentelemetry.trace as trace
from opentelemetry.context.propagation import httptextformat

_T = typing.TypeVar("_T")


class TraceContextHTTPTextFormat(httptextformat.HTTPTextFormat):
    """TODO: extracts and injects using w3c TraceContext's headers.
    """

    def extract(
        self, _get_from_carrier: httptextformat.Getter[_T], _carrier: _T
    ) -> trace.SpanContext:
        return trace.INVALID_SPAN_CONTEXT

    def inject(
        self,
        context: trace.SpanContext,
        set_in_carrier: httptextformat.Setter[_T],
        carrier: _T,
    ) -> None:
        pass
