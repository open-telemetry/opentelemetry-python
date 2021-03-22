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
import typing

from opentelemetry.context.context import Context


class TextMapPropagator(abc.ABC):
    """This class provides an interface that enables extracting and injecting
    context into headers of HTTP requests. HTTP frameworks and clients can
    integrate with TextMapPropagator by providing the object containing the
    headers.
    """

    @abc.abstractmethod
    def extract(
        self,
        carrier: typing.Dict[str, str],
        context: typing.Optional[Context] = None,
    ) -> Context:
        """Create a Context from values in the carrier.

        Retrieves values from the carrier object and uses them to populate a
        context and returns it afterwards.

        Args:
            carrier: and object which contains values that are used to
                construct a Context.
            context: an optional Context to use. Defaults to current context if
                not set.
        Returns:
            A Context with the configuration found in the carrier.
        """

    @abc.abstractmethod
    def inject(
        self,
        carrier: typing.Dict[str, str],
        context: typing.Optional[Context] = None,
    ) -> None:
        """Inject values from a Context into a carrier.

        Enables the propagation of values into HTTP clients or other objects
        which perform an HTTP request.

        Args:
            carrier: An dict-like object where to store HTTP headers.
            context: an optional Context to use. Defaults to current
                context if not set.

        """

    @property
    @abc.abstractmethod
    def fields(self) -> typing.Set[str]:
        """
        Gets the fields set in the carrier by the `inject` method.

        If the carrier is reused, its fields that correspond with the ones
        present in this attribute should be deleted before calling `inject`.

        Returns:
            A set with the fields set in `inject`.
        """
