"""Generate a dependency-free JSON Schema validator from ``schema.json``.

Validating a configuration file with ``jsonschema`` costs four extra runtime
dependencies: ``attrs``, ``referencing``, ``jsonschema-specifications`` and
``rpds-py``. The last of those is a compiled extension, so a distribution that
needs its installed tree to stay pure Python cannot use it, and ``jsonschema``'s
own floors (``attrs >= 22.2.0`` among them) can force an upgrade of a package
the application being instrumented has already pinned.

``fastjsonschema`` turns a schema into plain Python source instead. Running it
here, at development time rather than at import time, keeps ``fastjsonschema``
out of the runtime dependency set as well: the generated module imports
``decimal`` and the exception classes vendored next to it, and nothing else.

``detailed_exceptions=False`` keeps the generated module at roughly a fifth of
the size the detailed variant would be, which halves its cold import time. The
one thing it costs is the message for a missing required property, which
degrades to a bare ``data must contain`` naming no property at all. Since a
missing required key is the mistake a configuration file is most likely to
contain, this script restores those messages afterwards: every such check is
generated as an ``if <x>__missing_keys:`` guard whose variable already holds
the missing names, so the raise is rewritten to name them.

Run it after changing ``schema.json``::

    tox -e generate-config-validator

Forgetting to is caught rather than silent: ``tests/test_generated_validator.py``
recompiles the schema through ``compile_validator`` and fails when the result
differs from the committed ``_generated_validator.py``.

Known gap: ``fastjsonschema`` silently ignores keywords it does not implement
(``prefixItems``, ``unevaluatedProperties``, ``dependentRequired``,
``maxContains``). A schema that starts using one of them would be
under-enforced rather than rejected, so ``tests/test_generated_validator.py``
checks the schema against the set of keywords the generator understands.
"""

from json import loads
from pathlib import Path
from re import subn
from sys import exit as sys_exit
from typing import NamedTuple

from fastjsonschema import compile_to_code
from fastjsonschema import exceptions as fastjsonschema_exceptions

PACKAGE_ROOT: Path = Path(__file__).resolve().parent.parent / "src" / "opentelemetry" / "configuration"
SCHEMA: Path = PACKAGE_ROOT / "schema.json"
VALIDATOR: Path = PACKAGE_ROOT / "_generated_validator.py"
EXCEPTIONS: Path = PACKAGE_ROOT / "_validation_exceptions.py"

LICENSE_HEADER: str = "# Copyright The OpenTelemetry Authors\n# SPDX-License-Identifier: Apache-2.0\n\n"
TRUNCATED_REQUIRED_MESSAGE: str = ' must contain ")'
MISSING_KEYS_RAISE: str = (
    r"(?P<guard>[ ]*if (?P<variable>\w+__missing_keys):\n"
    r'[ ]*raise JsonSchemaValueException\(.*?) must contain "\)'
)
NAMED_KEYS_RAISE: str = r'\g<guard> must contain " + str(sorted(\g<variable>)) + " properties")'
VENDORED_IMPORT: str = (
    "from opentelemetry.configuration._validation_exceptions import (\n"
    "    JsonSchemaValueException,\n"
    "    JsonSchemaValuesException,\n"
    ")"
)


class UnexpectedGeneratorOutput(Exception):
    """Raised when fastjsonschema emits code this script no longer recognises."""


class CompiledValidator(NamedTuple):
    """The text of the validator module, and how many messages were repaired."""

    source: str
    repaired_messages: int


def compile_validator() -> CompiledValidator:
    """Compile ``schema.json`` into the text of ``_generated_validator.py``.

    Writes nothing. ``main`` writes the result to disk; the test suite compares
    it against the committed file so that a schema change without a
    regeneration fails instead of silently under-enforcing.
    """
    code: str = compile_to_code(loads(SCHEMA.read_text(encoding="utf-8")), detailed_exceptions=False)

    upstream_imports: list[str] = [line for line in code.splitlines() if line.startswith("from fastjsonschema import")]
    if len(upstream_imports) != 1:
        raise UnexpectedGeneratorOutput(
            f"expected exactly one 'from fastjsonschema import' line in the "
            f"generated code, found {len(upstream_imports)}: {upstream_imports}"
        )

    truncated: int = code.count(TRUNCATED_REQUIRED_MESSAGE)
    code, rewritten = subn(MISSING_KEYS_RAISE, NAMED_KEYS_RAISE, code)
    if rewritten != truncated:
        raise UnexpectedGeneratorOutput(
            f"expected every one of the {truncated} truncated 'must contain' "
            f"messages to sit under an '__missing_keys' guard, but only "
            f"{rewritten} did; fastjsonschema's code generation has changed"
        )

    body: str = code.replace(upstream_imports[0], VENDORED_IMPORT).rstrip("\n")

    return CompiledValidator(f"{LICENSE_HEADER}{body}\n", rewritten)


def vendored_exceptions_source() -> str:
    """Return the text of ``_validation_exceptions.py``, copied from fastjsonschema."""
    return Path(fastjsonschema_exceptions.__file__).read_text(encoding="utf-8")


def main() -> int:
    try:
        compiled: CompiledValidator = compile_validator()
    except UnexpectedGeneratorOutput as error:
        print(error)
        return 1

    VALIDATOR.write_text(compiled.source, encoding="utf-8")
    EXCEPTIONS.write_text(vendored_exceptions_source(), encoding="utf-8")

    rewritten: int = compiled.repaired_messages
    size: int = VALIDATOR.stat().st_size
    print(f"wrote {VALIDATOR.name} ({size} bytes)")
    print(f"wrote {EXCEPTIONS.name}")
    print(f"named the missing properties in {rewritten} required-key messages")
    return 0


if __name__ == "__main__":
    sys_exit(main())
