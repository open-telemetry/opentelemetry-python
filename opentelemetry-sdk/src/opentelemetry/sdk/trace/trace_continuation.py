# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import abc
import enum
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase
from logging import getLogger

from opentelemetry.context import Context
from opentelemetry.trace import Link, SpanKind
from opentelemetry.trace.span import SpanContext
from opentelemetry.util.types import AnyValue, Attributes

_logger = getLogger(__name__)


class ContinuationDirection(enum.Enum):
    INGRESS = 0
    EGRESS = 1


class Decision(enum.Enum):
    CONTINUE = 0
    RESTART_WITH_LINK = 1
    RESTART_WITHOUT_LINK = 2


class ContinuationResult:
    def __repr__(self) -> str:
        return f"{type(self).__name__}({str(self.decision)}, links={str(self.links)})"

    def __init__(
        self,
        *,
        decision: Decision,
        links: tuple[Link, ...] = (),
    ) -> None:
        self.decision = decision
        self.links = links

    @property
    def should_restart(self):
        return self.decision in (
            Decision.RESTART_WITH_LINK,
            Decision.RESTART_WITHOUT_LINK,
        )


class TraceContinuationDecider(abc.ABC):
    @abc.abstractmethod
    def should_continue(
        self,
        *,
        parent_context: Context | None,
        parent_span_context: SpanContext | None,
        direction: ContinuationDirection | None = None,
        kind: SpanKind | None = None,
        attributes: Attributes = None,
        links: tuple[Link, ...] | None = None,
    ) -> ContinuationResult:
        pass

    @abc.abstractmethod
    def get_description(self) -> str:
        pass


class StaticTraceContinuationDecider(TraceContinuationDecider):
    """Continuation decider that always returns the same decision."""

    def __init__(self, decision: Decision) -> None:
        self._decision = decision

    def should_continue(
        self,
        *,
        parent_context: Context | None,
        parent_span_context: SpanContext | None,
        direction: ContinuationDirection | None = None,
        kind: SpanKind | None = None,
        attributes: Attributes = None,
        links: tuple[Link, ...] | None = None,
    ) -> ContinuationResult:
        result_links = links or ()
        return ContinuationResult(
            decision=self._decision,
            links=_maybe_add_restart_link(
                decision=self._decision,
                parent_span_context=parent_span_context,
                links=result_links,
            ),
        )

    def get_description(self) -> str:
        if self._decision is Decision.RESTART_WITH_LINK:
            return "AlwaysRestartWithLinkContinuationDecider"
        if self._decision is Decision.RESTART_WITHOUT_LINK:
            return "AlwaysRestartWithoutLinkContinuationDecider"
        return "AlwaysContinueContinuationDecider"


ALWAYS_CONTINUE = StaticTraceContinuationDecider(Decision.CONTINUE)
ALWAYS_RESTART_WITH_LINK = StaticTraceContinuationDecider(
    Decision.RESTART_WITH_LINK
)
ALWAYS_RESTART_WITHOUT_LINK = StaticTraceContinuationDecider(
    Decision.RESTART_WITHOUT_LINK
)


@dataclass(frozen=True)
class TraceContinuationRule:
    """A rule that selects a trace continuation decision when all conditions match."""

    strategy: Decision
    attributes: Mapping[str, AnyValue] | None = None
    direction: ContinuationDirection | None = None
    span_kind: SpanKind | None = None
    link_attributes: Attributes = None

    def matches(
        self,
        *,
        direction: ContinuationDirection | None = None,
        span_kind: SpanKind | None = None,
        attributes: Attributes = None,
    ) -> bool:
        if self.direction is not None and direction != self.direction:
            return False
        if self.span_kind is not None and span_kind != self.span_kind:
            return False
        return _attributes_match(attributes, self.attributes)


class RuleBasedTraceContinuationDecider(TraceContinuationDecider):
    """Trace continuation decider with ordered first-match-wins rules."""

    def __init__(
        self,
        *,
        rules: Sequence[TraceContinuationRule],
        default_strategy: Decision = Decision.CONTINUE,
    ) -> None:
        self._rules = tuple(rules)
        self._default_strategy = default_strategy

    def should_continue(
        self,
        *,
        parent_context: Context | None,
        parent_span_context: SpanContext | None,
        direction: ContinuationDirection | None = None,
        kind: SpanKind | None = None,
        attributes: Attributes = None,
        links: tuple[Link, ...] | None = None,
    ) -> ContinuationResult:
        result_links = links or ()
        for rule in self._rules:
            if rule.matches(
                direction=direction,
                span_kind=kind,
                attributes=attributes,
            ):
                return ContinuationResult(
                    decision=rule.strategy,
                    links=_maybe_add_restart_link(
                        decision=rule.strategy,
                        parent_span_context=parent_span_context,
                        links=result_links,
                        link_attributes=rule.link_attributes,
                    ),
                )

        return ContinuationResult(
            decision=self._default_strategy,
            links=_maybe_add_restart_link(
                decision=self._default_strategy,
                parent_span_context=parent_span_context,
                links=result_links,
            ),
        )

    def get_description(self) -> str:
        return "RuleBasedTraceContinuationDecider"


def _maybe_add_restart_link(
    *,
    decision: Decision,
    parent_span_context: SpanContext | None,
    links: tuple[Link, ...],
    link_attributes: Attributes = None,
) -> tuple[Link, ...]:
    if decision is Decision.RESTART_WITH_LINK and parent_span_context:
        return links + (Link(parent_span_context, link_attributes),)
    return links


def _attributes_match(
    attributes: Attributes,
    expected_attributes: Mapping[str, AnyValue] | None,
) -> bool:
    if not expected_attributes:
        return True
    if not attributes:
        return False
    return all(
        key in attributes and _attribute_matches(attributes[key], expected)
        for key, expected in expected_attributes.items()
    )


def _attribute_matches(value: AnyValue, expected: AnyValue) -> bool:
    return any(
        _single_attribute_value_matches(actual, expected)
        for actual in _attribute_values(value)
    )


def _single_attribute_value_matches(
    value: AnyValue, expected: AnyValue
) -> bool:
    if isinstance(expected, str) and isinstance(value, str):
        return fnmatchcase(value, expected)
    return value == expected


def _attribute_values(value: AnyValue):
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return value
    return (value,)
