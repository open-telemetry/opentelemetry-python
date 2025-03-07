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

from logging import getLogger

from opentelemetry.sdk.error_handler import ErrorHandler

logger = getLogger(__name__)


# pylint: disable=too-many-ancestors
class ErrorHandler1(ErrorHandler, IndexError, KeyError):
    def _handle(self, error: Exception, *args, **kwargs):
        if isinstance(error, IndexError):
            logger.exception("ErrorHandler1 handling an IndexError")

        elif isinstance(error, KeyError):
            logger.exception("ErrorHandler1 handling a KeyError")
