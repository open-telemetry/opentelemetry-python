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

import base64
from opentelemetry.exporter.otlp.json.common.encoding import IdEncoding


def encode_id(id_encoding: IdEncoding, the_id: int, size: int) -> str:
    if id_encoding == IdEncoding.BASE64:
        return encode_to_base64(the_id, size)
    if id_encoding == IdEncoding.HEX:
        return encode_to_hex(the_id, size)
    raise ValueError(f"Unsupported encoding: {id_encoding}")


def encode_to_base64(the_id: int, size: int) -> str:
    """
    Encodes an integer as to a base64 string of a specified size.
    """
    if the_id < 0:
        raise ValueError("The ID must be a non-negative integer.")
    if size < 0:
        raise ValueError("Size must be a non-negative integer.")

    the_id_bytes = the_id.to_bytes(size, "big")
    return base64.b64encode(the_id_bytes).decode("ascii")


def encode_to_hex(the_id: int, size: int) -> str:
    """
    Encodes an integer to a hex string of a specified size.
    """
    if the_id < 0:
        raise ValueError("The ID must be a non-negative integer.")
    if size < 0:
        raise ValueError("Size must be a non-negative integer.")

    return hex(the_id)[2:].zfill(size * 2)
