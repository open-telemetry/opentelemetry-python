# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Hypothesis strategies shared by the fuzz targets."""

from collections.abc import Callable
from itertools import pairwise

from hypothesis import assume
from hypothesis import strategies as st

Mutation = Callable[[st.DrawFn, str], str]

_MAX_HEADERS = 4

# Whitespace allowed around list members (OWS, RFC 9110 section 5.6.3)
_OWS = " \t"


def char_mutations(chars: str) -> list[Mutation]:
    """Returns mutations that insert or replace a character with one of ``chars``, or delete a character."""

    def insert_char(draw: st.DrawFn, text: str) -> str:
        index = draw(st.integers(0, len(text)))
        return text[:index] + draw(st.sampled_from(chars)) + text[index:]

    def replace_char(draw: st.DrawFn, text: str) -> str:
        assume(text)
        index = draw(st.integers(0, len(text) - 1))
        return text[:index] + draw(st.sampled_from(chars)) + text[index + 1 :]

    def delete_char(draw: st.DrawFn, text: str) -> str:
        assume(text)
        index = draw(st.integers(0, len(text) - 1))
        return text[:index] + text[index + 1 :]

    return [insert_char, replace_char, delete_char]


@st.composite
def split_headers(draw: st.DrawFn, text: str) -> list[str]:
    """Splits a list at commas into between 1 and 4 header values, with optional OWS around each."""
    commas = [index for index, char in enumerate(text) if char == ","]
    splits = draw(st.sets(st.sampled_from(commas), max_size=_MAX_HEADERS - 1)) if commas else set()
    bounds = [-1, *sorted(splits), len(text)]
    ows = st.text(alphabet=_OWS, max_size=2)
    return [draw(ows) + text[start + 1 : end] + draw(ows) for start, end in pairwise(bounds)]
