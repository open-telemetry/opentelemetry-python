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

import re
from logging import getLogger

_logger = getLogger(__name__)

# The key MUST begin with a lowercase letter or a digit,
# and can only contain lowercase letters (a-z), digits (0-9),
# underscores (_), dashes (-), asterisks (*), and forward slashes (/).
# For multi-tenant vendor scenarios, an at sign (@) can be used to
# prefix the vendor name. Vendors SHOULD set the tenant ID
# at the beginning of the key.

# key = ( lcalpha ) 0*255( lcalpha / DIGIT / "_" / "-"/ "*" / "/" )
# key = ( lcalpha / DIGIT ) 0*240( lcalpha / DIGIT / "_" / "-"/ "*" / "/" ) "@" lcalpha 0*13( lcalpha / DIGIT / "_" / "-"/ "*" / "/" )
# lcalpha = %x61-7A ; a-z

_KEY_WITHOUT_VENDOR_FORMAT = r"[a-z][_0-9a-z\-\*\/]{0,255}"
_KEY_WITH_VENDOR_FORMAT = (
    r"[a-z0-9][_0-9a-z\-\*\/]{0,240}@[a-z][_0-9a-z\-\*\/]{0,13}"
)

_KEY_FORMAT = _KEY_WITHOUT_VENDOR_FORMAT + "|" + _KEY_WITH_VENDOR_FORMAT
_KEY_PATTERN = re.compile(_KEY_FORMAT)

# The value is an opaque string containing up to 256 printable
# ASCII [RFC0020] characters (i.e., the range 0x20 to 0x7E)
# except comma (,) and (=).
# value    = 0*255(chr) nblk-chr
# nblk-chr = %x21-2B / %x2D-3C / %x3E-7E
# chr      = %x20 / nblk-chr

_VALUE_FORMAT = (
    r"[\x20-\x2b\x2d-\x3c\x3e-\x7e]{0,255}[\x21-\x2b\x2d-\x3c\x3e-\x7e]"
)
_VALUE_PATTERN = re.compile(_VALUE_FORMAT)

_DELIMITER_FORMAT = "[ \t]*,[ \t]*"
_MEMBER_FORMAT = "({})(=)({})[ \t]*".format(_KEY_FORMAT, _VALUE_FORMAT)

_DELIMITER_PATTERN = re.compile(_DELIMITER_FORMAT)
_MEMBER_PATTERN = re.compile(_MEMBER_FORMAT)

_TRACECONTEXT_MAXIMUM_TRACESTATE_KEYS = 32


def _is_valid_key(key: str) -> bool:
    if not isinstance(key, str):
        return False
    return _KEY_PATTERN.fullmatch(key) is not None


def _is_valid_value(value: str) -> bool:
    if not isinstance(value, str):
        return False
    return _VALUE_PATTERN.fullmatch(value) is not None


def _is_valid_pair(key: str, value: str) -> bool:
    return _is_valid_key(key) and _is_valid_value(value)
