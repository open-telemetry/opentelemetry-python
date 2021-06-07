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

from opentelemetry.sdk.logs.severity import SeverityNumber

_STD_TO_OTLP = {
    10: SeverityNumber.DEBUG,
    11: SeverityNumber.DEBUG2,
    12: SeverityNumber.DEBUG3,
    13: SeverityNumber.DEBUG4,
    14: SeverityNumber.DEBUG4,
    15: SeverityNumber.DEBUG4,
    16: SeverityNumber.DEBUG4,
    17: SeverityNumber.DEBUG4,
    18: SeverityNumber.DEBUG4,
    19: SeverityNumber.DEBUG4,
    20: SeverityNumber.INFO,
    21: SeverityNumber.INFO2,
    22: SeverityNumber.INFO3,
    23: SeverityNumber.INFO4,
    24: SeverityNumber.INFO4,
    25: SeverityNumber.INFO4,
    26: SeverityNumber.INFO4,
    27: SeverityNumber.INFO4,
    28: SeverityNumber.INFO4,
    29: SeverityNumber.INFO4,
    30: SeverityNumber.WARN,
    31: SeverityNumber.WARN2,
    32: SeverityNumber.WARN3,
    33: SeverityNumber.WARN4,
    34: SeverityNumber.WARN4,
    35: SeverityNumber.WARN4,
    36: SeverityNumber.WARN4,
    37: SeverityNumber.WARN4,
    38: SeverityNumber.WARN4,
    39: SeverityNumber.WARN4,
    40: SeverityNumber.ERROR,
    41: SeverityNumber.ERROR2,
    42: SeverityNumber.ERROR3,
    43: SeverityNumber.ERROR4,
    44: SeverityNumber.ERROR4,
    45: SeverityNumber.ERROR4,
    46: SeverityNumber.ERROR4,
    47: SeverityNumber.ERROR4,
    48: SeverityNumber.ERROR4,
    49: SeverityNumber.ERROR4,
    50: SeverityNumber.FATAL,
    51: SeverityNumber.FATAL2,
    52: SeverityNumber.FATAL3,
    53: SeverityNumber.FATAL4,
}


def std_to_otlp(levelno: int) -> SeverityNumber:
    """Map python log levelno to OTLP log severity number."""
    if levelno < 10:
        return SeverityNumber.UNSPECIFIED
    if levelno > 53:
        return SeverityNumber.FATAL4
    return _STD_TO_OTLP[levelno]
