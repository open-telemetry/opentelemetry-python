# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The interface a cross-process propagator implements.

A propagator serializes part of a :class:`~opentelemetry.context.Context` into
a carrier when a request leaves the process, and reads it back when one
arrives. The carrier is whatever the transport exposes, most often a mapping
of HTTP headers.

A propagator never touches the carrier directly. It reads through a
:class:`Getter` and writes through a :class:`Setter`, so one propagator works
with any carrier shape as long as a getter and a setter exist for it.
``default_getter`` and ``default_setter`` cover a plain mapping.
"""

import abc
import typing
from collections.abc import Iterable, Mapping, MutableMapping

from opentelemetry.context.context import Context

CarrierT = typing.TypeVar("CarrierT")
# pylint: disable=invalid-name
CarrierValT = list[str] | str


class Getter(abc.ABC, typing.Generic[CarrierT]):
    """This class implements a Getter that enables extracting propagated
    fields from a carrier.
    """

    @abc.abstractmethod
    def get(self, carrier: CarrierT, key: str) -> list[str] | None:
        """Function that can retrieve zero
        or more values from the carrier. In the case that
        the value does not exist, returns None.

        Args:
            carrier: An object which contains values that are used to
                    construct a Context.
            key: key of a field in carrier.

        Returns:
            Every value stored under ``key``, or ``None`` when the key does not
            exist in the carrier.
        """

    @abc.abstractmethod
    def keys(self, carrier: CarrierT) -> list[str]:
        """Function that can retrieve all the keys in a carrier object.

        Args:
            carrier: An object which contains values that are
                used to construct a Context.

        Returns:
            list of keys from the carrier.
        """


class Setter(abc.ABC, typing.Generic[CarrierT]):
    """This class implements a Setter that enables injecting propagated
    fields into a carrier.
    """

    @abc.abstractmethod
    def set(self, carrier: CarrierT, key: str, value: str) -> None:
        """Function that can set a value into a carrier.

        Args:
            carrier: An object which contains values that are used to
                    construct a Context.
            key: key of a field in carrier.
            value: value for a field in carrier.
        """


class DefaultGetter(Getter[Mapping[str, CarrierValT]]):
    """A :class:`Getter` for a carrier that is a plain mapping.

    This is the getter used when a caller passes HTTP headers as a dict and
    supplies no getter of their own. ``default_getter`` is a ready-made
    instance.
    """

    def get(self, carrier: Mapping[str, CarrierValT], key: str) -> list[str] | None:
        """Getter implementation to retrieve a value from a dictionary.

        Args:
            carrier: dictionary in which to get value
            key: the key used to get the value

        Returns:
            A list with a single string with the value if it exists, else None.
            A value that is itself a non-string iterable is returned as a list
            of its items, which is how a repeated header is handled.
        """
        val = carrier.get(key, None)
        if val is None:
            return None
        if isinstance(val, Iterable) and not isinstance(val, str):
            return list(val)
        return [val]

    def keys(self, carrier: Mapping[str, CarrierValT]) -> list[str]:
        """Keys implementation that returns all keys from a dictionary.

        Args:
            carrier: dictionary whose keys to return

        Returns:
            Every key in the carrier, in iteration order.
        """
        return list(carrier.keys())


default_getter: Getter[CarrierT] = DefaultGetter()  # type: ignore


class DefaultSetter(Setter[MutableMapping[str, CarrierValT]]):
    """A :class:`Setter` for a carrier that is a plain mutable mapping.

    Setting a key that is already present replaces it. ``default_setter``
    is a ready-made instance.
    """

    def set(
        self,
        carrier: MutableMapping[str, CarrierValT],
        key: str,
        value: CarrierValT,
    ) -> None:
        """Setter implementation to set a value into a dictionary.

        Args:
            carrier: dictionary in which to set value
            key: the key used to set the value
            value: the value to set
        """
        carrier[key] = value


default_setter: Setter[CarrierT] = DefaultSetter()  # type: ignore


class TextMapPropagator(abc.ABC):
    """This class provides an interface that enables extracting and injecting
    context into headers of HTTP requests. HTTP frameworks and clients
    can integrate with TextMapPropagator by providing the object containing the
    headers, and a getter and setter function for the extraction and
    injection of values, respectively.

    """

    @abc.abstractmethod
    def extract(
        self,
        carrier: CarrierT,
        context: Context | None = None,
        getter: Getter[CarrierT] = default_getter,
    ) -> Context:
        """Create a Context from values in the carrier.

        The extract function should retrieve values from the carrier
        object using getter, and use values to populate a
        Context value and return it.

        Args:
            getter: a function that can retrieve zero
                or more values from the carrier. In the case that
                the value does not exist, return an empty list.
            carrier: and object which contains values that are
                used to construct a Context. This object
                must be paired with an appropriate getter
                which understands how to extract a value from it.
            context: an optional Context to use. Defaults to root
                context if not set.

        Returns:
            A Context with configuration found in the carrier.
        """

    @abc.abstractmethod
    def inject(
        self,
        carrier: CarrierT,
        context: Context | None = None,
        setter: Setter[CarrierT] = default_setter,
    ) -> None:
        """Inject values from a Context into a carrier.

        inject enables the propagation of values into HTTP clients or
        other objects which perform an HTTP request. Implementations
        should use the `Setter` 's set method to set values on the
        carrier.

        Args:
            carrier: An object that a place to define HTTP headers.
                Should be paired with setter, which should
                know how to set header values on the carrier.
            context: an optional Context to use. Defaults to current
                context if not set.
            setter: An optional `Setter` object that can set values
                on the carrier.

        """

    @property
    @abc.abstractmethod
    def fields(self) -> set[str]:
        """
        Gets the fields set in the carrier by the `inject` method.

        If the carrier is reused, its fields that correspond with the ones
        present in this attribute should be deleted before calling `inject`.

        Returns:
            A set with the fields set in `inject`.
        """
