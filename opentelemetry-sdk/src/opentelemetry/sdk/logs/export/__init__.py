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

import abc
import enum
from typing import Sequence

from opentelemetry.sdk.logs import LogData


class LogExportResult(enum.Enum):
    SUCCESS = 0
    FAILURE = 1


class LogExporter(abc.ABC):
    """Interface for exporting logs.

    Interface to be implemented by services that want to export logs received
    in their own format.

    To export data this MUST be registered to the :class`opentelemetry.sdk.logs.LogEmitter` using a
    log processor.
    """

    @abc.abstractmethod
    def export(self, batch: Sequence[LogData]):
        """Exports a batch of logs.

        Args:
            batch: The list of `LogData` objects to be exported

        Returns:
            The result of the export
        """

    @abc.abstractmethod
    def shutdown(self):
        """Shuts down the exporter.

        Called when the SDK is shut down.
        """
