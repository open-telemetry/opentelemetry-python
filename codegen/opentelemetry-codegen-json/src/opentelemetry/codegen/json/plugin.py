# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=no-member

import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager

from google.protobuf.compiler import plugin_pb2 as plugin

from opentelemetry.codegen.json.generator import generate_plugin_response
from opentelemetry.codegen.json.version import __version__

_logger = logging.getLogger(__name__)


@contextmanager
def code_generation() -> Iterator[
    tuple[plugin.CodeGeneratorRequest, plugin.CodeGeneratorResponse],
]:
    """
    Context manager for handling the code generation process.
    """
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
    """
    Main entry point for the protoc plugin.
    """
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
