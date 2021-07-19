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

from logging import getLogger
from sys import modules

from pkg_resources import iter_entry_points

_logger = getLogger(__name__)

_loaded = False

_current_module = modules[__name__]
_current_module_attributes = set(dir(_current_module))

if not _loaded:
    for entry_point in iter_entry_points(
        "opentelemetry_environment_variables"
    ):

        other_module = entry_point.load()

        for attribute in dir(other_module):

            if attribute.startswith("OTEL_"):

                value = getattr(other_module, attribute)

                if attribute in _current_module_attributes:
                    # pylint: disable=logging-not-lazy
                    # pylint: disable=logging-format-interpolation
                    _logger.warning(
                        "Overriding value of {} with {}".format(
                            attribute, value
                        )
                    )

                setattr(
                    _current_module,
                    attribute,
                    getattr(other_module, attribute),
                )

                _current_module_attributes.add(attribute)

_loaded = True
