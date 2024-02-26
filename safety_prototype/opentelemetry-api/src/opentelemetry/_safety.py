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

from functools import wraps
from warnings import warn, resetwarnings
from traceback import format_exception
from sys import exc_info


def _safe_function(predefined_return_value):
    """
    This is the safety mechanism mentioned in the README file.

    This is used as a decorator on every function or method in the API.
    """

    def internal(function):
        @wraps(function)
        def wrapper(*args, **kwargs):

            # This is the try / except block mentioned in the README file.
            try:
                exception = None
                return function(*args, **kwargs)
            except Exception:  # pylint: disable=broad-except
                exception = "".join(format_exception(*exc_info()))

            if exception is not None:
                # This is the warning mentioned in the README file.
                warn(f"OpenTelemetry handled an exception:\n\n{exception}")
                exception = None
                resetwarnings()

            return predefined_return_value

        return wrapper

    return internal
