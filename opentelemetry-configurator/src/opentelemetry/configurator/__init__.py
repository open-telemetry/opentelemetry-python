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


from abc import ABC, abstractmethod
from os import environ

from pkg_resources import iter_entry_points

from opentelemetry.configurator.environment_variables import (
    OTEL_PYTHON_CONFIGURATORS,
)


def _configure():

    installed_configurators = {
        entry_point.name: entry_point
        for entry_point in iter_entry_points("opentelemetry-configurator")
    }

    configured_configurator_names = environ.get(
        OTEL_PYTHON_CONFIGURATORS, ""
    ).split()

    if len(installed_configurators) > 1 and not (
        configured_configurator_names
    ):

        raise Exception(
            "More than 1 configurator is available:\n\n\t{}\n"
            "Select the ones that are to be used by setting "
            "{}.".format(
                "\n\t".join(list(installed_configurators.keys())),
                OTEL_PYTHON_CONFIGURATORS,
            )
        )

    for configured_configurator_name in environ.get(
        OTEL_PYTHON_CONFIGURATORS, ""
    ).split():

        if configured_configurator_name in installed_configurators.keys():

            installed_configurators[
                configured_configurator_name
            ].load()().configure()


class BaseConfigurator(ABC):
    @abstractmethod
    def configure(self):
        pass
