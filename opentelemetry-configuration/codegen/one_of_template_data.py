# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Write datamodel-codegen ``--extra-template-data`` for one-of schema types.

The configuration schema expresses "exactly one component choice" (e.g. a
``Sampler`` is one of ``always_on``, ``always_off``, ...) as
``minProperties: 1, maxProperties: 1``. datamodel-codegen does not pass those
keywords to templates, so this script derives a per-model
``exactly_one_property`` flag from the schema for ``dataclass.jinja2`` to
consume.

Usage:
    python one_of_template_data.py SCHEMA_JSON OUTPUT_JSON
"""

import json
import sys
from pathlib import Path


def one_of_template_data(schema: dict) -> dict[str, dict[str, bool]]:
    """Map each one-of ``$defs`` model name to ``{"exactly_one_property": True}``."""
    return {
        definition.get("title", name): {"exactly_one_property": True}
        for name, definition in schema.get("$defs", {}).items()
        if definition.get("minProperties") == 1 and definition.get("maxProperties") == 1
    }


def main(argv: list[str]) -> None:
    schema_path, output_path = argv
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    Path(output_path).write_text(json.dumps(one_of_template_data(schema), indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])
