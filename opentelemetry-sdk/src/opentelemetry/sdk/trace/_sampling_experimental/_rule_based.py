# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Routing a span to one of several composable samplers by predicate.

A rule is a pair of a predicate and a composable sampler. The rules are tried
in order and the first predicate that returns ``True`` wins, so ordering
carries meaning and a broad rule placed early hides the narrower rules after
it. A span that matches no rule is dropped.

The predicates in this module look at one aspect of the span each: an
attribute value, the span kind, or the relationship to the parent. Combine
them with ``AllPredicate``, and end the rule list with ``AlwaysMatchPredicate``
when a catch-all is wanted instead of the default drop.

Private to the ``_sampling_experimental`` subpackage, with no compatibility
guarantee.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from fnmatch import fnmatchcase
from typing import Protocol

from opentelemetry.context import Context
from opentelemetry.trace import (
    Link,
    SpanKind,
    TraceState,
    get_current_span,
)
from opentelemetry.util.types import AnyValue, Attributes

from ._composable import ComposableSampler, SamplingIntent
from ._util import INVALID_THRESHOLD


class PredicateT(Protocol):
    """The test a rule applies to decide whether its sampler is used.

    Implementations take the same arguments as ``sampling_intent`` and answer
    with a plain boolean. They are called once per span, in rule order, until
    one matches, so keep them cheap and free of side effects.
    """

    def __call__(
        self,
        parent_ctx: Context | None,
        name: str,
        span_kind: SpanKind | None,
        attributes: Attributes,
        links: Sequence[Link] | None,
        trace_state: TraceState | None,
    ) -> bool:
        """Report whether this predicate matches the span about to be created.

        ``_ComposableRuleBased`` passes all six arguments by keyword, so an
        implementation must keep these parameter names.

        Args:
            parent_ctx: Context holding the parent span, or ``None`` to mean
                the current context.
            name: The name the span will be created with.
            span_kind: The kind the span will be created with, or ``None``.
            attributes: The attributes known at creation time, or ``None``.
            links: The links the span will be created with, or ``None``.
            trace_state: The trace state inherited from the parent, or
                ``None``.

        Returns:
            ``True`` when the rule holding this predicate should be used.
        """
        ...  # pylint: disable=unnecessary-ellipsis

    def __str__(self) -> str:
        """Render the predicate for the rule-based sampler's description.

        Returns:
            A short form of the test, with no surrounding punctuation. The
            rule-based sampler embeds it in its own description.
        """
        ...  # pylint: disable=unnecessary-ellipsis


class AttributePredicate:
    """An exact match of an attribute value

    Superseded by ``AttributeValuesPredicate``, which accepts several values
    and looks inside sequence-valued attributes. Constructing this class logs
    a deprecation warning on the root logger, once per construction.

    The comparison is ``==`` on the raw attribute value, with no string
    conversion, so an integer attribute does not match a string value. Both
    ``key`` and ``value`` are public and read on every call, so changing them
    after construction changes what the predicate matches.

    Args:
        key: The attribute name to look up.
        value: The value the attribute has to equal.
    """

    def __init__(self, key: str, value: AnyValue):
        """Build the instance and log the deprecation warning.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        logging.warning("This is deprecated, use AttributeValuesPredicate instead")
        self.key = key
        self.value = value

    def __call__(
        self,
        parent_ctx: Context | None,
        name: str,
        span_kind: SpanKind | None,
        attributes: Attributes,
        links: Sequence[Link] | None,
        trace_state: TraceState | None,
    ) -> bool:
        """Report whether the attribute equals the configured value.

        Args:
            parent_ctx: Ignored.
            name: Ignored.
            span_kind: Ignored.
            attributes: The attributes known at creation time. ``None`` or an
                empty mapping never matches, even when the configured value
                is itself ``None``.
            links: Ignored.
            trace_state: Ignored.

        Returns:
            ``True`` when the attribute compares equal. A missing key reads as
            ``None``, so a predicate built with a value of ``None`` matches
            any span that carries at least one attribute.
        """
        if not attributes:
            return False
        return attributes.get(self.key) == self.value

    def __str__(self):
        """Render the predicate as ``key=value``.

        Returns:
            The key and the value joined by ``=``, with the value formatted
            by ``str``.
        """
        return f"{self.key}={self.value}"


class AlwaysMatchPredicate:
    """A predicate that matches every span.

    Put a rule holding this predicate last in the rule list to give the
    rule-based sampler a fallback. Without one, a span matching no rule is
    dropped.
    """

    def __call__(
        self,
        parent_ctx: Context | None,
        name: str,
        span_kind: SpanKind | None,
        attributes: Attributes,
        links: Sequence[Link] | None,
        trace_state: TraceState | None,
    ) -> bool:
        """Match unconditionally.

        Args:
            parent_ctx: Ignored.
            name: Ignored.
            span_kind: Ignored.
            attributes: Ignored.
            links: Ignored.
            trace_state: Ignored.

        Returns:
            Always ``True``.
        """
        return True

    def __str__(self) -> str:
        """Render the predicate.

        Returns:
            The constant ``"AlwaysMatch"``.
        """
        return "AlwaysMatch"


class AllPredicate:
    """The conjunction of several predicates.

    The sequence is copied into a tuple at construction, so changing the
    sequence afterwards has no effect. Evaluation short circuits on the first
    predicate that fails, which means ordering within the sequence is a
    performance choice and not a semantic one.

    An empty sequence matches everything, following the usual reading of a
    conjunction over nothing.

    Args:
        predicates: The predicates that all have to match. Each receives the
            same six arguments this predicate was called with.
    """

    def __init__(self, predicates: Sequence[PredicateT]):
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._predicates = tuple(predicates)

    def __call__(
        self,
        parent_ctx: Context | None,
        name: str,
        span_kind: SpanKind | None,
        attributes: Attributes,
        links: Sequence[Link] | None,
        trace_state: TraceState | None,
    ) -> bool:
        """Report whether every configured predicate matches.

        Args:
            parent_ctx: Forwarded to each predicate.
            name: Forwarded to each predicate.
            span_kind: Forwarded to each predicate.
            attributes: Forwarded to each predicate.
            links: Forwarded to each predicate.
            trace_state: Forwarded to each predicate.

        Returns:
            ``True`` when all of them match, and ``True`` when there are none.
        """
        return all(
            predicate(
                parent_ctx,
                name,
                span_kind,
                attributes,
                links,
                trace_state,
            )
            for predicate in self._predicates
        )

    def __str__(self) -> str:
        """Render the conjunction.

        Returns:
            The rendering of each predicate joined by `` && ``, in the order
            they were given. An empty sequence renders as the empty string.
        """
        return " && ".join(str(predicate) for predicate in self._predicates)


class AttributeValuesPredicate:
    """A match of an attribute against a set of allowed string values.

    Comparison runs on ``str`` of the attribute value, so an attribute holding
    the integer ``8080`` matches the value ``"8080"``. The allowed values are
    taken as given and are not converted, so pass them as strings.

    An attribute holding a sequence matches when any of its elements matches.
    A string, ``bytes`` or ``bytearray`` attribute counts as a single value
    rather than a sequence of characters.

    Args:
        key: The attribute name to look up. A span without this key never
            matches.
        values: The allowed values, copied into a frozen set, so order and
            duplicates do not matter and later edits to the sequence have no
            effect.
    """

    def __init__(self, key: str, values: Sequence[str]):
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._key = key
        self._values = frozenset(values)

    def __call__(
        self,
        parent_ctx: Context | None,
        name: str,
        span_kind: SpanKind | None,
        attributes: Attributes,
        links: Sequence[Link] | None,
        trace_state: TraceState | None,
    ) -> bool:
        """Report whether the attribute holds one of the allowed values.

        Args:
            parent_ctx: Ignored.
            name: Ignored.
            span_kind: Ignored.
            attributes: The attributes known at creation time. ``None``, an
                empty mapping, or a mapping without the configured key all
                fail to match.
            links: Ignored.
            trace_state: Ignored.

        Returns:
            ``True`` when the attribute, or any element of it when it is a
            sequence, stringifies to one of the allowed values. An empty set
            of allowed values never matches.
        """
        if not attributes or self._key not in attributes:
            return False
        return any(str(value) in self._values for value in _attribute_values(attributes[self._key]))

    def __str__(self) -> str:
        """Render the predicate as ``key in [a,b,c]``.

        Returns:
            The key, the word ``in``, and the allowed values sorted and
            comma separated inside square brackets. Sorting keeps the
            rendering stable across runs, which a frozen set would not.
        """
        values = ",".join(sorted(self._values))
        return f"{self._key} in [{values}]"


class AttributePatternsPredicate:
    """Match attribute values using a callable receiving a value and a pattern.

    By default, patterns use case-sensitive ``fnmatchcase`` semantics.

    A value is accepted when it matches at least one included pattern and no
    excluded pattern, with exclusion winning over inclusion. Leaving
    ``included`` empty means every value is included, which turns the
    predicate into a pure exclusion list. Leaving both empty makes it match
    any span that carries the key, unless the attribute holds an empty
    sequence, which matches nothing because there is no element to accept.

    An attribute holding a sequence matches when any of its elements is
    accepted. Values are stringified before matching.

    Args:
        key: The attribute name to look up. A span without this key never
            matches.
        included: Patterns at least one of which has to match, or ``None``
            for no inclusion requirement. Copied into a tuple.
        excluded: Patterns none of which may match, or ``None`` for no
            exclusions. Copied into a tuple.
        matcher: Keyword-only callable taking the value first and the pattern
            second, returning whether they match. The default is
            ``fnmatchcase``, so matching is case sensitive. Pass something
            else to use regular expressions or prefix matching instead.
    """

    def __init__(
        self,
        key: str,
        included: Sequence[str] | None = None,
        excluded: Sequence[str] | None = None,
        *,
        matcher: Callable[[str, str], bool] = fnmatchcase,
    ):
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._matcher = matcher
        self._key = key
        self._included = tuple(included or ())
        self._excluded = tuple(excluded or ())

    def __call__(
        self,
        parent_ctx: Context | None,
        name: str,
        span_kind: SpanKind | None,
        attributes: Attributes,
        links: Sequence[Link] | None,
        trace_state: TraceState | None,
    ) -> bool:
        """Report whether the attribute holds an accepted value.

        Args:
            parent_ctx: Ignored.
            name: Ignored.
            span_kind: Ignored.
            attributes: The attributes known at creation time. ``None``, an
                empty mapping, or a mapping without the configured key all
                fail to match.
            links: Ignored.
            trace_state: Ignored.

        Returns:
            ``True`` when the attribute, or any element of it when it is a
            sequence, passes the included and excluded pattern lists.
        """
        if not attributes or self._key not in attributes:
            return False
        return any(self._matches_value(str(value)) for value in _attribute_values(attributes[self._key]))

    def _matches_value(self, value: str) -> bool:
        """Apply the included and excluded pattern lists to one value.

        Args:
            value: The attribute value, already converted with ``str``.

        Returns:
            ``True`` when the value matches an included pattern, or there are
            no included patterns, and matches no excluded pattern. Exclusion
            takes precedence, so a value matching both lists is rejected.
        """
        included = not self._included or any(self._matcher(value, pattern) for pattern in self._included)
        excluded = any(self._matcher(value, pattern) for pattern in self._excluded)
        return included and not excluded

    def __str__(self) -> str:
        """Render the predicate as ``key matches``.

        The patterns themselves do not appear, so two predicates on the same
        key with different patterns render identically.

        Returns:
            The key followed by the word ``matches``.
        """
        return f"{self._key} matches"


class SpanKindPredicate:
    """A match on the kind of the span.

    This is the filter that lets a rule apply to, say, server and consumer
    spans while leaving internal spans to a later rule. The comparison is set
    membership on the ``SpanKind`` enum, with no widening, so a span created
    without a kind never matches: ``None`` is outside the declared type of
    ``span_kinds``.

    Args:
        span_kinds: The kinds that match, copied into a frozen set. An empty
            sequence matches nothing.
    """

    def __init__(self, span_kinds: Sequence[SpanKind]):
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._span_kinds = frozenset(span_kinds)

    def __call__(
        self,
        parent_ctx: Context | None,
        name: str,
        span_kind: SpanKind | None,
        attributes: Attributes,
        links: Sequence[Link] | None,
        trace_state: TraceState | None,
    ) -> bool:
        """Report whether the span kind is one of the configured kinds.

        Args:
            parent_ctx: Ignored.
            name: Ignored.
            span_kind: The kind the span will be created with, or ``None``
                when the caller supplied none, in which case nothing matches.
            attributes: Ignored.
            links: Ignored.
            trace_state: Ignored.

        Returns:
            ``True`` when the kind is in the configured set.
        """
        return span_kind in self._span_kinds

    def __str__(self) -> str:
        """Render the predicate as ``span_kind in [server,client]``.

        Returns:
            The kind names lowercased and comma separated inside square
            brackets. The order follows the frozen set, so it is not
            guaranteed to match the order the kinds were given in.

        Raises:
            AttributeError: If ``None`` was included in the configured kinds,
                since ``None`` has no ``name``.
        """
        kinds = ",".join(kind.name.lower() for kind in self._span_kinds)
        return f"span_kind in [{kinds}]"


class ParentPredicate:
    """A match on how the span relates to its parent.

    The parent is classified into exactly one of three names: ``"none"`` when
    the parent span context is not valid, which is a root span, ``"remote"``
    when the parent arrived over the wire, and ``"local"`` otherwise.

    Args:
        parents: The names that match, copied into a frozen set. Only
            ``"none"``, ``"remote"`` and ``"local"`` can ever match; any other
            string is accepted without complaint and simply never matches.
    """

    def __init__(self, parents: Sequence[str]):
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._parents = frozenset(parents)

    def __call__(
        self,
        parent_ctx: Context | None,
        name: str,
        span_kind: SpanKind | None,
        attributes: Attributes,
        links: Sequence[Link] | None,
        trace_state: TraceState | None,
    ) -> bool:
        """Report whether the parent falls into one of the configured classes.

        Args:
            parent_ctx: Context holding the parent span. ``None`` means the
                current context, so this is not the same as having no parent:
                an ambient active span is still found and classified.
            name: Ignored.
            span_kind: Ignored.
            attributes: Ignored.
            links: Ignored.
            trace_state: Ignored.

        Returns:
            ``True`` when the class of the parent, one of ``"none"``,
            ``"remote"`` or ``"local"``, is in the configured set.
        """
        parent_span_context = get_current_span(parent_ctx).get_span_context()
        if not parent_span_context.is_valid:
            parent = "none"
        elif parent_span_context.is_remote:
            parent = "remote"
        else:
            parent = "local"
        return parent in self._parents

    def __str__(self) -> str:
        """Render the predicate as ``parent in [remote,local]``.

        Returns:
            The configured names comma separated inside square brackets. The
            order follows the frozen set, so it varies and does not reflect
            the order the names were given in.
        """
        parents = ",".join(self._parents)
        return f"parent in [{parents}]"


def _attribute_values(value):
    """Normalise one attribute value into an iterable of values to test.

    An attribute may hold a scalar or a sequence, and the predicates in this
    module treat both the same way by iterating. Text and byte values are
    sequences in Python but are meant as single values here, so they are
    wrapped rather than iterated character by character.

    Args:
        value: The raw attribute value.

    Returns:
        The value itself when it is a sequence that is not ``str``, ``bytes``
        or ``bytearray``, and a one-element tuple holding it otherwise.
    """
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return (value,)


RulesT = Sequence[tuple[PredicateT, ComposableSampler]]

_non_sampling_intent = SamplingIntent(threshold=INVALID_THRESHOLD, threshold_reliable=False)


class _ComposableRuleBased(ComposableSampler):
    """Composable sampler that picks a delegate by the first matching rule.

    Rules are tried in the order given. The first predicate that returns
    ``True`` decides which sampler is asked for the intent, and no later rule
    is consulted. A span matching no rule gets ``_non_sampling_intent``, which
    drops it.

    Args:
        rules: Pairs of predicate and composable sampler. The sequence is
            copied at construction, so adding or removing rules afterwards
            has no effect on an already built sampler.
    """

    def __init__(self, rules: RulesT):
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        # work on an internal copy of the rules
        self._rules = list(rules)

    def sampling_intent(
        self,
        parent_ctx: Context | None,
        name: str,
        span_kind: SpanKind | None,
        attributes: Attributes,
        links: Sequence[Link] | None,
        trace_state: TraceState | None = None,
    ) -> SamplingIntent:
        """Ask the first matching rule's sampler for the intent.

        Predicates and the chosen sampler are both called with these six
        arguments passed by keyword, so a custom predicate or sampler has to
        keep the parameter names.

        Args:
            parent_ctx: Forwarded to each predicate and to the chosen sampler.
            name: Forwarded to each predicate and to the chosen sampler.
            span_kind: Forwarded to each predicate and to the chosen sampler.
            attributes: Forwarded to each predicate and to the chosen sampler.
            links: Forwarded to each predicate and to the chosen sampler.
            trace_state: Forwarded to each predicate and to the chosen
                sampler. Defaults to ``None``, which the protocol does not.

        Returns:
            The intent from the sampler of the first rule whose predicate
            matched. When no rule matches, a shared intent with
            ``INVALID_THRESHOLD`` and an unreliable threshold, which drops the
            span, so an empty rule list drops everything.
        """
        for predicate, sampler in self._rules:
            if predicate(
                parent_ctx=parent_ctx,
                name=name,
                span_kind=span_kind,
                attributes=attributes,
                links=links,
                trace_state=trace_state,
            ):
                return sampler.sampling_intent(
                    parent_ctx=parent_ctx,
                    name=name,
                    span_kind=span_kind,
                    attributes=attributes,
                    links=links,
                    trace_state=trace_state,
                )
        return _non_sampling_intent

    def get_description(self) -> str:
        """Describe the sampler and every rule it holds.

        The descriptions of the delegate samplers are read on each call, so a
        delegate whose description depends on mutable state is re-read here.

        Returns:
            A string of the form ``ComposableRuleBased{[(pred:desc),...]}``,
            with one parenthesised pair per rule in rule order, the predicate
            rendered by ``str`` and the sampler by its own description.
        """
        rules_str = ",".join(f"({predicate}:{sampler.get_description()})" for predicate, sampler in self._rules)
        return f"ComposableRuleBased{{[{rules_str}]}}"


def composable_rule_based(
    rules: RulesT,
) -> ComposableSampler:
    """Returns a consistent sampler that:

    - Evaluates a series of rules based on predicates and returns the SamplingIntent from the first matching sampler
    - If no rules match, returns a non-sampling intent

    Args:
        rules: A list of (Predicate, ComposableSampler) pairs, where Predicate
            is a function that evaluates whether a rule applies

    Returns:
        A new sampler holding a copy of ``rules``. Each call builds a fresh
        instance. Order the rules from most specific to least specific, since
        the first match wins and the remaining rules are not consulted.
    """
    return _ComposableRuleBased(rules)
