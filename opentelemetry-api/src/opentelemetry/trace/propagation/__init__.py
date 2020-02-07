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
from typing import Optional

from opentelemetry.trace import INVALID_SPAN_CONTEXT, Span, SpanContext

_SPAN_CONTEXT_KEY = "extracted-span-context"
_SPAN_KEY = "current-span"


def get_span_key(tracer_source_id: Optional[str] = None) -> str:
    key = _SPAN_KEY
    if tracer_source_id is not None:
        key = "{}-{}".format(key, tracer_source_id)
    return key
