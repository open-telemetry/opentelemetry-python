# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# type: ignore

import logging
from types import MappingProxyType
from typing import MutableSequence, Optional, Sequence, Tuple

from opentelemetry.util import types

_VALID_ATTR_VALUE_TYPES = (bool, str, int, float)


_logger = logging.getLogger(__name__)


def _clean_attribute_value(
    value: types.AttributeValue, max_size: Optional[int]
) -> Tuple[bool, Optional[types.AttributeValue]]:
    """Checks if attribute value is valid.

    An attribute value is valid if it is either:
        - A primitive type: string, boolean, double precision floating
            point (IEEE 754-1985) or integer.
        - An array of primitive type values. The array MUST be homogeneous,
            i.e. it MUST NOT contain values of different types.

    This function tries to clean attribute values according to the following rules:
    - bytes are decoded to strings.
    - When ``max_size`` argument is set, any string/bytes values longer than the value
    are truncated to the specified max length.
    - ``Sequence`` values other than strings such as lists are converted to immutable tuples.


    If the attribute value is modified or converted to another type, the new value is returned
    as the second return value.
    If the attribute value is not modified, ``None`` is returned as the second return value.
    """

    # pylint: disable=too-many-branches
    modified = False
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        if len(value) == 0:
            return True, None

        sequence_first_valid_type = None
        new_value = []
        for element in value:
            if element is None:
                new_value.append(element)
                continue
            element_type = type(element)
            if element_type not in _VALID_ATTR_VALUE_TYPES:
                _logger.warning(
                    "Invalid type %s in attribute value sequence. Expected one of "
                    "%s or None",
                    element_type.__name__,
                    [
                        valid_type.__name__
                        for valid_type in _VALID_ATTR_VALUE_TYPES
                    ],
                )
                return False, None
            # The type of the sequence must be homogeneous. The first non-None
            # element determines the type of the sequence
            if sequence_first_valid_type is None:
                sequence_first_valid_type = element_type
            elif not isinstance(element, sequence_first_valid_type):
                _logger.warning(
                    "Mixed types %s and %s in attribute value sequence",
                    sequence_first_valid_type.__name__,
                    type(element).__name__,
                )
                return False, None
            if max_size is not None and isinstance(element, str):
                element = element[:max_size]
                modified = True
            new_value.append(element)
        # Freeze mutable sequences defensively
        if isinstance(value, MutableSequence):
            modified = True
        value = tuple(new_value)

    elif isinstance(value, bytes):
        try:
            value = value.decode()
            modified = True
        except ValueError:
            _logger.warning("Byte attribute could not be decoded.")
            return False, None

    elif not isinstance(value, _VALID_ATTR_VALUE_TYPES):
        _logger.warning(
            "Invalid type %s for attribute value. Expected one of %s or a "
            "sequence of those types",
            type(value).__name__,
            [valid_type.__name__ for valid_type in _VALID_ATTR_VALUE_TYPES],
        )
        return False, None

    if max_size is not None and isinstance(value, str):
        value = value[:max_size]
        modified = True
    return True, value if modified else None


def _clean_attributes(
    attributes: types.Attributes, max_size: Optional[int]
) -> None:
    """Applies attribute validation rules and truncates/drops (key, value) pairs
    that doesn't adhere to attributes specification.

    https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/common/common.md#attributes.
    """
    if not attributes:
        return

    for attr_key, attr_value in list(attributes.items()):
        if not attr_key:
            _logger.warning("invalid key `%s` (empty or null)", attr_key)
            attributes.pop(attr_key)
            continue

        valid, cleaned_value = _clean_attribute_value(attr_value, max_size)
        if not valid:
            attributes.pop(attr_key)
            continue

        if cleaned_value is not None:
            attributes[attr_key] = cleaned_value


def _create_immutable_attributes(
    attributes: types.Attributes,
) -> types.Attributes:
    return MappingProxyType(attributes.copy() if attributes else {})
