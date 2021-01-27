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

import os
import sys
from logging import getLogger

from pkg_resources import iter_entry_points

from opentelemetry.configuration import Configuration

logger = getLogger(__file__)


def _load_distros():
    for entry_point in iter_entry_points("opentelemetry_distro"):
        try:
            entry_point.load()().configure()  # type: ignore
            logger.debug("Distribution %s configured", entry_point.name)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Distribution %s configuration failed", entry_point.name
            )
            raise exc


def _load_instrumentors():
    package_to_exclude = Configuration().get("DISABLED_INSTRUMENTATIONS", [])
    if isinstance(package_to_exclude, str):
        package_to_exclude = package_to_exclude.split(",")
        # to handle users entering "requests , flask" or "requests, flask" with spaces
        package_to_exclude = [x.strip() for x in package_to_exclude]

    for entry_point in iter_entry_points("opentelemetry_instrumentor"):
        try:
            if entry_point.name in package_to_exclude:
                logger.debug(
                    "Instrumentation skipped for library %s", entry_point.name
                )
                continue
            entry_point.load()().instrument()  # type: ignore
            logger.debug("Instrumented %s", entry_point.name)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Instrumenting of %s failed", entry_point.name)
            raise exc


def _load_configurators():
    configured = None
    for entry_point in iter_entry_points("opentelemetry_configurator"):
        if configured is not None:
            logger.warning(
                "Configuration of %s not loaded, %s already loaded",
                entry_point.name,
                configured,
            )
            continue
        try:
            entry_point.load()().configure()  # type: ignore
            configured = entry_point.name
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Configuration of %s failed", entry_point.name)
            raise exc


def initialize():
    try:
        _load_distros()
        _load_configurators()
        _load_instrumentors()
    except Exception:  # pylint: disable=broad-except
        logger.exception("Failed to auto initialize opentelemetry")


if (
    hasattr(sys, "argv")
    and sys.argv[0].split(os.path.sep)[-1] == "celery"
    and "worker" in sys.argv[1:]
):
    from celery.signals import worker_process_init  # pylint:disable=E0401

    @worker_process_init.connect(weak=False)
    def init_celery(*args, **kwargs):
        initialize()


else:
    initialize()
