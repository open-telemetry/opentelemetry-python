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

import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Tuple

from google.protobuf.compiler import plugin_pb2 as plugin

from opentelemetry.codegen.json.generator import generate_plugin_response
from opentelemetry.codegen.json.version import __version__

_logger = logging.getLogger(__name__)


@contextmanager
def code_generation() -> Iterator[
    Tuple[plugin.CodeGeneratorRequest, plugin.CodeGeneratorResponse],
]:
    if len(sys.argv) > 1 and sys.argv[1] in ("-V", "--version"):
        print("opentelemetry-codegen-json " + __version__)
        sys.exit(0)

    data = sys.stdin.buffer.read()

    request = plugin.CodeGeneratorRequest()
    request.ParseFromString(data)

    response = plugin.CodeGeneratorResponse()

    yield request, response

    output = response.SerializeToString()
    sys.stdout.buffer.write(output)


def main() -> None:
    with code_generation() as (request, response):
        generated_response = generate_plugin_response(request)

        response.supported_features |= generated_response.supported_features
        for file in generated_response.file:
            response.file.add().CopyFrom(file)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        stream=sys.stderr,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    main()
