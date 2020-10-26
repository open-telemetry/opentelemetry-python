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

from typing import Dict, Sequence

from wrapt import ObjectProxy

from opentelemetry.trace.status import StatusCode


def extract_attributes_from_object(
    obj: any, attributes: Sequence[str], existing: Dict[str, str] = None
) -> Dict[str, str]:
    extracted = {}
    if existing:
        extracted.update(existing)
    for attr in attributes:
        value = getattr(obj, attr, None)
        if value is not None:
            extracted[attr] = str(value)
    return extracted


def http_status_to_canonical_code(
    status: int, allow_redirect: bool = True
) -> StatusCode:
    """Converts an HTTP status code to an OpenTelemetry canonical status code

    Args:
        status (int): HTTP status code
    """
    # pylint:disable=too-many-branches,too-many-return-statements
    # if status < 100:
    #     return StatusCode.UNKNOWN
    # if status <= 299:
    #     return StatusCode.OK
    # if status <= 399:
    #     if allow_redirect:
    #         return StatusCode.OK
    #     return StatusCode.DEADLINE_EXCEEDED
    # if status <= 499:
    #     if status == 401:  # HTTPStatus.UNAUTHORIZED:
    #         return StatusCode.UNAUTHENTICATED
    #     if status == 403:  # HTTPStatus.FORBIDDEN:
    #         return StatusCode.PERMISSION_DENIED
    #     if status == 404:  # HTTPStatus.NOT_FOUND:
    #         return StatusCode.NOT_FOUND
    #     if status == 429:  # HTTPStatus.TOO_MANY_REQUESTS:
    #         return StatusCode.RESOURCE_EXHAUSTED
    #     return StatusCode.INVALID_ARGUMENT
    # if status <= 599:
    #     if status == 501:  # HTTPStatus.NOT_IMPLEMENTED:
    #         return StatusCode.UNIMPLEMENTED
    #     if status == 503:  # HTTPStatus.SERVICE_UNAVAILABLE:
    #         return StatusCode.UNAVAILABLE
    #     if status == 504:  # HTTPStatus.GATEWAY_TIMEOUT:
    #         return StatusCode.DEADLINE_EXCEEDED
    #     return StatusCode.INTERNAL
    # return StatusCode.UNKNOWN
    return StatusCode.OK


def unwrap(obj, attr: str):
    """Given a function that was wrapped by wrapt.wrap_function_wrapper, unwrap it

    Args:
        obj: Object that holds a reference to the wrapped function
        attr (str): Name of the wrapped function
    """
    func = getattr(obj, attr, None)
    if func and isinstance(func, ObjectProxy) and hasattr(func, "__wrapped__"):
        setattr(obj, attr, func.__wrapped__)
