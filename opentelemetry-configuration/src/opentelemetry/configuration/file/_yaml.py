# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""YAML 1.2 Core schema loader for declarative configuration files.

PyYAML implements YAML 1.1. The OpenTelemetry file-configuration spec requires
YAML 1.2 parsed with the Core schema
(https://yaml.org/spec/1.2.2/#103-core-schema), so plain scalars are resolved
by this loader only.

``yaml.loader.SafeLoader`` is the pure-Python loader. ``yaml.SafeLoader`` is an
alias of the libyaml ``CSafeLoader`` when that extension is installed, and the
C loader ignores a Python resolver table. Subclassing the pure-Python loader
is what makes the Core schema take effect.

Resolver and constructor tables are created on this subclass. They are never
the lists stored on ``SafeLoader`` / ``Resolver``, so loading a configuration
file cannot change PyYAML's own YAML 1.1 behavior.
"""

from __future__ import annotations

import math
import re

from yaml.constructor import BaseConstructor, ConstructorError
from yaml.loader import SafeLoader
from yaml.nodes import MappingNode, ScalarNode

_NULL_TAG = "tag:yaml.org,2002:null"
_BOOL_TAG = "tag:yaml.org,2002:bool"
_INT_TAG = "tag:yaml.org,2002:int"
_FLOAT_TAG = "tag:yaml.org,2002:float"

# YAML 1.2.2 §10.3.2 tag resolution. Patterns are end-anchored because
# PyYAML applies them with ``re.match``.
_NULL_RE = re.compile(r"^(?:null|Null|NULL|~|)\Z")
_BOOL_RE = re.compile(r"^(?:true|True|TRUE|false|False|FALSE)\Z")
# Base 10 (leading zeros are decimal, not YAML 1.1 octal), ``0o`` octal, ``0x`` hex.
# No sign on the prefixed forms, and no ``0b``, ``_``, or sexagesimal ``1:20``.
_INT_RE = re.compile(r"^(?:0o[0-7]+|[-+]?[0-9]+|0x[0-9a-fA-F]+)\Z")
_FLOAT_RE = re.compile(
    r"^(?:"
    r"[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?"
    r"|[-+]?\.(?:inf|Inf|INF)"
    r"|\.(?:nan|NaN|NAN)"
    r")\Z"
)

# SafeLoader still constructs these YAML 1.1 tags. Core schema does not
# define them, so an explicit ``!!timestamp`` / ``!!binary`` / ``!!merge``
# is an error instead of a silently different type.
_NON_CORE_TAGS = frozenset(
    {
        "tag:yaml.org,2002:binary",
        "tag:yaml.org,2002:timestamp",
        "tag:yaml.org,2002:omap",
        "tag:yaml.org,2002:pairs",
        "tag:yaml.org,2002:set",
        "tag:yaml.org,2002:value",
        "tag:yaml.org,2002:merge",
    }
)


class _YAML12CoreLoader(SafeLoader):  # pylint: disable=too-many-ancestors
    """Parse configuration YAML with the YAML 1.2 Core schema.

    ``yes`` / ``on`` / ``y`` stay strings, ``1:20`` stays a string, ``010`` is
    decimal 10, and ``0o10`` is octal 8. Timestamps, merge keys (``<<``), and
    the value tag (``=``) are not special.
    """

    def construct_yaml_bool(self, node: ScalarNode) -> bool:
        """Build a Core schema bool (``true`` / ``false`` only)."""
        value = self._scalar_text(node, "boolean")
        if not _BOOL_RE.fullmatch(value):
            raise ConstructorError(
                None,
                None,
                f"expected a YAML 1.2 boolean, but found {node.value!r}",
                node.start_mark,
            )
        return value.lower() == "true"

    def construct_yaml_int(self, node: ScalarNode) -> int:
        """Build a Core schema int.

        PyYAML's constructor reads a leading zero as octal, so ``010`` would
        become 8 and ``08`` would raise. Core schema base-10 integers are
        decimal, including leading zeros.
        """
        value = self._scalar_text(node, "integer")
        if not _INT_RE.fullmatch(value):
            raise ConstructorError(
                None,
                None,
                f"expected a YAML 1.2 integer, but found {node.value!r}",
                node.start_mark,
            )
        # ``int`` accepts the ``0o`` / ``0x`` prefix. Base 10 is explicit so a
        # leading zero stays decimal: ``010`` is 10, not YAML 1.1 octal 8.
        if value.startswith("0o"):
            return int(value, 8)
        if value.startswith("0x"):
            return int(value, 16)
        return int(value, 10)

    def construct_yaml_float(self, node: ScalarNode) -> float:
        """Build a Core schema float, with no sexagesimal or signed-NaN form."""
        raw = self._scalar_text(node, "float")
        if not _FLOAT_RE.fullmatch(raw):
            raise ConstructorError(
                None,
                None,
                f"expected a YAML 1.2 float, but found {node.value!r}",
                node.start_mark,
            )
        value = raw.lower()
        sign = -1.0 if value[0] == "-" else 1.0
        if value[0] in "+-":
            value = value[1:]
        if value == ".inf":
            return math.copysign(math.inf, sign)
        if value == ".nan":
            return math.nan
        return sign * float(value)

    def construct_mapping(self, node: MappingNode, deep: bool = False) -> dict:
        """Build a mapping without YAML 1.1 merge (``<<``) or value (``=``) keys."""
        return BaseConstructor.construct_mapping(self, node, deep=deep)

    def construct_scalar(self, node: ScalarNode | MappingNode):
        """Return the scalar text. Do not unwrap a YAML 1.1 value-tagged key."""
        if not isinstance(node, ScalarNode):
            raise ConstructorError(
                None,
                None,
                f"expected a scalar node, but found {node.id}",
                node.start_mark,
            )
        return BaseConstructor.construct_scalar(self, node)

    def _scalar_text(self, node: ScalarNode, kind: str) -> str:
        value = self.construct_scalar(node)
        if not isinstance(value, str) or value == "":
            raise ConstructorError(
                None,
                None,
                f"expected a YAML 1.2 {kind}, but found {value!r}",
                node.start_mark,
            )
        return value


# A subclass that does not yet own ``yaml_implicit_resolvers`` makes
# ``add_implicit_resolver`` copy the base lists and then append. Starting
# from an empty dict keeps YAML 1.1 resolvers off this loader and keeps the
# appends off ``SafeLoader``.
_YAML12CoreLoader.yaml_implicit_resolvers = {}
_YAML12CoreLoader.add_implicit_resolver(_BOOL_TAG, _BOOL_RE, list("tTfF"))
_YAML12CoreLoader.add_implicit_resolver(_INT_TAG, _INT_RE, list("-+0123456789"))
_YAML12CoreLoader.add_implicit_resolver(_FLOAT_TAG, _FLOAT_RE, list("-+0123456789."))
_YAML12CoreLoader.add_implicit_resolver(_NULL_TAG, _NULL_RE, ["~", "n", "N", ""])

# Copy, then drop YAML 1.1 tags, then replace bool/int/float. ``add_constructor``
# copies on first use only when the subclass has no table of its own; assign
# the filtered copy first so ``SafeLoader.yaml_constructors`` is not updated.
_YAML12CoreLoader.yaml_constructors = {
    tag: constructor for tag, constructor in SafeLoader.yaml_constructors.items() if tag not in _NON_CORE_TAGS
}
_YAML12CoreLoader.add_constructor(_BOOL_TAG, _YAML12CoreLoader.construct_yaml_bool)
_YAML12CoreLoader.add_constructor(_INT_TAG, _YAML12CoreLoader.construct_yaml_int)
_YAML12CoreLoader.add_constructor(_FLOAT_TAG, _YAML12CoreLoader.construct_yaml_float)
