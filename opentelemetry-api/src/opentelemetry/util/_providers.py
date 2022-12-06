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
from os import environ
from sys import version_info
from typing import TYPE_CHECKING, TypeVar, cast

from opentelemetry.util._entry_points import entry_points

if TYPE_CHECKING:
    from opentelemetry.metrics import MeterProvider
    from opentelemetry.trace import TracerProvider

Provider = TypeVar("Provider", "TracerProvider", "MeterProvider")

logger = getLogger(__name__)


def _load_provider(
    provider_environment_variable: str, provider: str
) -> Provider:

    try:

        # FIXME remove when support for 3.9 is dropped.
        if version_info.minor in (8, 9):

            provider_name = cast(
                str,
                environ.get(
                    provider_environment_variable, f"default_{provider}"
                ),
            )

            for entry_point in entry_points()[f"opentelemetry_{provider}"]:  # type: ignore
                if entry_point.name == provider_name:  # type: ignore
                    return cast(Provider, entry_point.load()())  # type: ignore
            raise Exception(f"Provider {provider_name} not found")

        return cast(
            Provider,
            next(  # type: ignore
                iter(  # type: ignore
                    entry_points(  # type: ignore
                        group=f"opentelemetry_{provider}",
                        name=cast(
                            str,
                            environ.get(
                                provider_environment_variable,
                                f"default_{provider}",
                            ),
                        ),
                    )
                )
            ).load()(),
        )
    except Exception:  # pylint: disable=broad-except
        logger.exception("Failed to load configured provider %s", provider)
        raise
