# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import abc
import enum
from logging import getLogger

from opentelemetry.context import Context
from opentelemetry.trace import Link, SpanKind
from opentelemetry.trace.span import SpanContext
from opentelemetry.util.types import Attributes

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
        if (
            self._decision is Decision.RESTART_WITH_LINK
            and parent_span_context
        ):
            result_links += (Link(parent_span_context),)
        return ContinuationResult(
            decision=self._decision,
            links=result_links,
        )

    def get_description(self) -> str:
        if self._decision is Decision.RESTART_WITH_LINK:
            return "AlwaysRestartWithLinkContinuationDecider"
        elif self._decision is Decision.RESTART_WITHOUT_LINK:
            return "AlwaysRestartWithoutLinkContinuationDecider"
        return "AlwaysContinueContinuationDecider"


ALWAYS_CONTINUE = StaticTraceContinuationDecider(Decision.CONTINUE)
ALWAYS_RESTART_WITH_LINK = StaticTraceContinuationDecider(
    Decision.RESTART_WITH_LINK
)
ALWAYS_RESTART_WITHOUT_LINK = StaticTraceContinuationDecider(
    Decision.RESTART_WITHOUT_LINK
)
