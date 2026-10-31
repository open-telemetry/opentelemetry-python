# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Errors raised when a bucket boundary is not a representable float.

Both errors come out of ``get_lower_boundary``, never out of
``map_to_index``, so they report a bucket index that no float can
describe rather than a measurement the mapping cannot handle.
"""


class MappingUnderflowError(Exception):
    """
    Raised when computing the lower boundary of an index that maps into a
    denormal floating point value.
    """


class MappingOverflowError(Exception):
    """
    Raised when computing the lower boundary of an index that maps into +inf.
    """
