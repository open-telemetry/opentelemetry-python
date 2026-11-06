# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""A stand-in for an ``importlib.metadata`` entry point.

Several packages pick an implementation by name from an entry point group, for
example ``opentelemetry_tracer_provider``. Testing that selection against real
entry points would mean installing a distribution, so a test patches
``entry_points`` to return instances of :class:`IterEntryPoint` instead.
"""


class IterEntryPoint:
    """An entry point that loads a class given to it rather than importing one.

    Only the ``name`` attribute and the ``load`` method are provided, which is
    the part of the ``importlib.metadata.EntryPoint`` interface the selection
    code uses. ``value``, ``group`` and ``dist`` are absent, so code that reads
    those raises ``AttributeError``.

    Args:
        name: The entry point name, which is what selection code matches a
            configured value against.
        class_type: The object ``load`` returns. Named for the usual case of a
            class, but nothing checks it, so any object works.
    """

    def __init__(self, name, class_type):
        """Parameters are documented on the class docstring."""
        self.name = name
        self.class_type = class_type

    def load(self):
        """Return the object this entry point stands for.

        Returns:
            The object passed as ``class_type``, returned as it is. No import
            happens and no module is executed, so an entry point that would fail
            to import in reality cannot be simulated with this class.
        """
        return self.class_type
