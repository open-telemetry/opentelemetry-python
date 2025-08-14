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

import pytest

from opentelemetry.sdk.trace._sampling_experimental._trace_state import (
    OtelTraceState,
)
from opentelemetry.trace import TraceState


@pytest.mark.parametrize(
    "input_str,output_str",
    (
        ("a", "a"),
        ("#", "#"),
        ("rv:1234567890abcd", "rv:1234567890abcd"),
        ("rv:01020304050607", "rv:01020304050607"),
        ("rv:1234567890abcde", ""),
        ("th:1234567890abcd", "th:1234567890abcd"),
        ("th:1234567890abcd", "th:1234567890abcd"),
        ("th:10000000000000", "th:1"),
        ("th:1234500000000", "th:12345"),
        ("th:0", "th:0"),
        ("th:100000000000000", ""),
        ("th:1234567890abcde", ""),
        pytest.param(
            f"a:{'X' * 214};rv:1234567890abcd;th:1234567890abcd;x:3",
            f"th:1234567890abcd;rv:1234567890abcd;a:{'X' * 214};x:3",
            id="long",
        ),
        ("th:x", ""),
        ("th:100000000000000", ""),
        ("th:10000000000000", "th:1"),
        ("th:1000000000000", "th:1"),
        ("th:100000000000", "th:1"),
        ("th:10000000000", "th:1"),
        ("th:1000000000", "th:1"),
        ("th:100000000", "th:1"),
        ("th:10000000", "th:1"),
        ("th:1000000", "th:1"),
        ("th:100000", "th:1"),
        ("th:10000", "th:1"),
        ("th:1000", "th:1"),
        ("th:100", "th:1"),
        ("th:10", "th:1"),
        ("th:1", "th:1"),
        ("th:10000000000001", "th:10000000000001"),
        ("th:10000000000010", "th:1000000000001"),
        ("rv:x", ""),
        ("rv:100000000000000", ""),
        ("rv:10000000000000", "rv:10000000000000"),
        ("rv:1000000000000", ""),
    ),
)
def test_marshal(input_str: str, output_str: str):
    state = OtelTraceState.parse(TraceState((("ot", input_str),))).serialize()
    assert state == output_str
