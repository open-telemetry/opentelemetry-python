# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Entry-point lookup used to resolve the globally configured providers.

The API never imports an SDK directly. Instead it reads the name of the wanted
implementation from an environment variable and loads the matching
``opentelemetry_*`` entry point, which is what :func:`_load_provider` does.
"""

from logging import getLogger
from os import environ
from typing import TYPE_CHECKING, TypeVar, cast

if TYPE_CHECKING:
    from opentelemetry.metrics import MeterProvider
    from opentelemetry.trace import TracerProvider

Provider = TypeVar("Provider", "TracerProvider", "MeterProvider")

logger = getLogger(__name__)


def _load_provider(provider_environment_variable: str, provider: str) -> Provider:  # type: ignore[type-var]
    """Instantiate the provider implementation named by an environment variable.

    The value of ``provider_environment_variable`` is looked up as an entry
    point name in the ``opentelemetry_{provider}`` group. When the variable is
    unset, the name ``default_{provider}`` is used instead. The entry point is
    loaded and called with no argument to build the provider.

    Args:
        provider_environment_variable: Name of the environment variable holding
            the entry point name to load, for example
            ``"OTEL_PYTHON_TRACER_PROVIDER"``.
        provider: Suffix identifying the entry point group and the default
            entry point name, for example ``"tracer_provider"``.

    Returns:
        A newly constructed provider of the type matching ``provider``.

    Raises:
        Exception: Re-raises whatever the lookup or the construction raised,
            after logging it. A missing entry point surfaces as
            :exc:`StopIteration`.
    """
    # pylint: disable=import-outside-toplevel,no-name-in-module
    from opentelemetry.util._importlib_metadata import (  # noqa: PLC0415
        entry_points,
    )

    try:
        provider_name = cast(
            str,
            environ.get(provider_environment_variable, f"default_{provider}"),
        )

        return cast(
            Provider,
            next(  # type: ignore
                iter(  # type: ignore
                    entry_points(  # type: ignore
                        group=f"opentelemetry_{provider}",
                        name=provider_name,
                    )
                )
            ).load()(),
        )
    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("Failed to load configured provider %s", provider)
        raise
