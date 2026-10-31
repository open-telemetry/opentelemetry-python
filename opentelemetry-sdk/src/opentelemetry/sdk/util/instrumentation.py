# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
"""Identity of the code that emitted a piece of telemetry.

Every tracer, meter and logger the SDK hands out carries an
``InstrumentationScope`` built from the name, version, schema url and
attributes passed to ``get_tracer``, ``get_meter`` or ``get_logger``. The SDK
groups spans, metrics and log records by that scope when it exports them, and
a view or a processor can select on it.

``InstrumentationInfo`` is the earlier form of the same idea, without the
attributes. It is deprecated and kept so that older exporters keep importing.
"""

from collections.abc import Callable
from fnmatch import fnmatchcase
from json import dumps

from typing_extensions import deprecated

from opentelemetry.attributes import BoundedAttributes
from opentelemetry.util.types import (  # TODO: see if we can remove F401 when using new sphinx version # noqa: F401 # pylint: disable=unused-import
    AnyValue,
    Attributes,
)


class InstrumentationInfo:
    """Immutable information about an instrumentation library module.

    See `opentelemetry.trace.TracerProvider.get_tracer` for the meaning of these
    properties.

    Deprecated since version 1.11.1. Use ``InstrumentationScope``, which also
    carries attributes.

    Args:
        name: The name the instrumentation passed to ``get_tracer``, usually
            the import name of the instrumenting module.
        version: The version of the instrumenting module, or ``None`` when it
            did not give one.
        schema_url: The url of the semantic convention schema the emitted
            telemetry follows. ``None`` is stored as the empty string, so
            ``schema_url`` never reads back as ``None``.
    """

    __slots__ = ("_name", "_version", "_schema_url")

    @deprecated("You should use InstrumentationScope. Deprecated since version 1.11.1.")
    def __init__(
        self,
        name: str,
        version: str | None = None,
        schema_url: str | None = None,
    ):
        """Build the instance and warn that the class is deprecated.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._name = name
        self._version = version
        if schema_url is None:
            schema_url = ""
        self._schema_url = schema_url

    def __repr__(self):
        """Render the name, the version and the schema url.

        Returns:
            A string of the form ``InstrumentationInfo(name, version,
            schema_url)``. The fields are not quoted, so the result is not
            valid Python.
        """
        return f"{type(self).__name__}({self._name}, {self._version}, {self._schema_url})"

    def __hash__(self):
        """Hash the name, the version and the schema url together.

        Returns:
            A hash consistent with ``__eq__``, so two instances built from
            the same three values land in the same bucket of a dict or a set.
        """
        return hash((self._name, self._version, self._schema_url))

    def __eq__(self, value):
        """Compare the name, the version and the schema url.

        Args:
            value: The object to compare against. Anything whose type is not
                exactly this class compares unequal, including a subclass
                instance and an ``InstrumentationScope``.

        Returns:
            ``True`` when the two carry the same three values.
        """
        return type(value) is type(self) and (
            self._name,
            self._version,
            self._schema_url,
        ) == (value._name, value._version, value._schema_url)

    def __lt__(self, value):
        """Order by name, then version, then schema url.

        The ordering exists so that a list of scopes can be sorted into a
        stable export order. Tuple comparison stops at the first element that
        differs, so a ``None`` version is only reached when the two names are
        equal, and it raises ``TypeError`` then because ``None`` and a string
        cannot be compared. Instances with distinct names sort whether or not
        they carry a version.

        Args:
            value: The object to compare against.

        Returns:
            ``True`` when this instance sorts first. ``NotImplemented`` when
            ``value`` is not of exactly this type, which makes Python fall
            back to the reflected operation and then raise ``TypeError``.
        """
        if type(value) is not type(self):
            return NotImplemented
        return (self._name, self._version, self._schema_url) < (
            value._name,
            value._version,
            value._schema_url,
        )

    @property
    def schema_url(self) -> str | None:
        """The schema url passed to the constructor.

        Returns:
            The url, or the empty string when the constructor was given
            ``None``.
        """
        return self._schema_url

    @property
    def version(self) -> str | None:
        """The version passed to the constructor.

        Returns:
            The version string, or ``None`` when the instrumentation did not
            report one.
        """
        return self._version

    @property
    def name(self) -> str:
        """The name passed to the constructor.

        Returns:
            The name, unchanged. It is not validated, so an empty name is
            possible.
        """
        return self._name


class InstrumentationScope:
    """A logical unit of the application code with which the emitted telemetry can be
    associated.

    See `opentelemetry.trace.TracerProvider.get_tracer` for the meaning of these
    properties.

    An instance is used as a dict key by the exporters, which group the spans,
    metrics and log records they receive by the scope that produced them.

    Args:
        name: The name the instrumentation passed to ``get_tracer``,
            ``get_meter`` or ``get_logger``, usually the import name of the
            instrumenting module.
        version: The version of the instrumenting module, or ``None`` when it
            did not give one.
        schema_url: The url of the semantic convention schema the emitted
            telemetry follows. ``None`` is stored as the empty string, so
            ``schema_url`` never reads back as ``None``.
        attributes: Scope attributes, stored in an immutable
            ``BoundedAttributes``, so they cannot be added to or removed
            after construction. ``None`` gives an empty mapping rather than
            ``None``.
    """

    __slots__ = (
        "_name",
        "_version",
        "_schema_url",
        "_attributes",
    )

    def __init__(
        self,
        name: str,
        version: str | None = None,
        schema_url: str | None = None,
        attributes: Attributes = None,
    ) -> None:
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._name = name
        self._version = version
        if schema_url is None:
            schema_url = ""
        self._schema_url = schema_url
        # Attributes cannot be added/removed after creation.
        self._attributes = BoundedAttributes(attributes=attributes, immutable=True)

    def __repr__(self) -> str:
        """Render the name, the version, the schema url and the attributes.

        Returns:
            A string of the form ``InstrumentationScope(name, version,
            schema_url, attributes)``. The fields are not quoted, so the
            result is not valid Python.
        """
        return f"{type(self).__name__}({self._name}, {self._version}, {self._schema_url}, {self._attributes})"

    def __hash__(self) -> int:
        """Hash the name, the version and the schema url together.

        The attributes are left out, because the mapping holding them does
        not hash. Two scopes that differ only in their attributes therefore
        share a hash while comparing unequal, which a dict handles as an
        ordinary collision.

        Returns:
            A hash over the three string fields.
        """
        return hash((self._name, self._version, self._schema_url))

    def __eq__(self, value: object) -> bool:
        """Compare the name, the version, the schema url and the attributes.

        Args:
            value: The object to compare against. Anything that is not an
                ``InstrumentationScope`` yields ``NotImplemented``, which
                makes Python fall back to the reflected comparison and then
                to identity.

        Returns:
            ``True`` when all four fields are equal.
        """
        if not isinstance(value, InstrumentationScope):
            return NotImplemented
        return (
            self._name,
            self._version,
            self._schema_url,
            self._attributes,
        ) == (
            value._name,
            value._version,
            value._schema_url,
            value._attributes,
        )

    def __lt__(self, value: object) -> bool:
        """Order by name, then version, then schema url, then attributes.

        The ordering exists so that a list of scopes can be sorted into a
        stable export order. Tuple comparison stops at the first element that
        differs, so the attributes are only reached by two scopes that agree
        on the three string fields, and they raise ``TypeError`` only when
        they are themselves unequal, since comparing two
        ``BoundedAttributes`` with ``<`` is not supported. Two scopes that
        are equal throughout sort without raising.

        Args:
            value: The object to compare against.

        Returns:
            ``True`` when this instance sorts first. ``NotImplemented`` when
            ``value`` is not an ``InstrumentationScope``.
        """
        if not isinstance(value, InstrumentationScope):
            return NotImplemented
        return (
            self._name,
            self._version,
            self._schema_url,
            self._attributes,
        ) < (
            value._name,
            value._version,
            value._schema_url,
            value._attributes,
        )

    @property
    def schema_url(self) -> str | None:
        """The schema url passed to the constructor.

        Returns:
            The url, or the empty string when the constructor was given
            ``None``.
        """
        return self._schema_url

    @property
    def version(self) -> str | None:
        """The version passed to the constructor.

        Returns:
            The version string, or ``None`` when the instrumentation did not
            report one.
        """
        return self._version

    @property
    def name(self) -> str:
        """The name passed to the constructor.

        Returns:
            The name, unchanged. It is not validated, so an empty name is
            possible.
        """
        return self._name

    @property
    def attributes(self) -> Attributes:
        """The scope attributes.

        Returns:
            The immutable ``BoundedAttributes`` built at construction.
            Assigning into it raises ``TypeError``. It is empty rather than
            ``None`` when no attributes were given.
        """
        return self._attributes

    def to_json(self, indent: int | None = 4) -> str:
        """Serialise the scope to JSON, for a console exporter or a log line.

        Args:
            indent: The number of spaces to indent each nesting level by, as
                ``json.dumps`` takes it. Pass ``None`` for the compact
                single-line form.

        Returns:
            A JSON object with ``name``, ``version``, ``schema_url`` and
            ``attributes``. The ``attributes`` member is ``null`` rather than
            an empty object when the scope carries none.
        """
        return dumps(
            {
                "name": self._name,
                "version": self._version,
                "schema_url": self._schema_url,
                "attributes": (dict(self._attributes) if bool(self._attributes) else None),
            },
            indent=indent,
        )


_InstrumentationScopePredicateT = Callable[[InstrumentationScope], bool]


def _scope_name_matches_glob(
    glob_pattern: str,
) -> _InstrumentationScopePredicateT:
    """Build a predicate that tests a scope name against a glob pattern.

    Args:
        glob_pattern: A pattern in the syntax ``fnmatch`` accepts, so ``*``
            matches any run of characters, ``?`` matches one, and ``[seq]``
            matches one character of the set. A pattern with no wildcard in
            it matches only the exact name.

    Returns:
        A function that takes an ``InstrumentationScope`` and reports whether
        its name matches, comparing case sensitively on every platform.
    """

    def inner(scope: InstrumentationScope) -> bool:
        """Report whether the name of ``scope`` matches the captured pattern.

        Args:
            scope: The scope whose name is tested. Only the name is looked
                at; the version, the schema url and the attributes are
                ignored.

        Returns:
            ``True`` when the name matches.
        """
        # Scope name matching is case-sensitive. fnmatchcase is used instead of
        # fnmatch so it does not rely on the host platform's filename case
        # sensitivity (normcase), which lower-cases both operands on Windows.
        return fnmatchcase(scope.name, glob_pattern)

    return inner
