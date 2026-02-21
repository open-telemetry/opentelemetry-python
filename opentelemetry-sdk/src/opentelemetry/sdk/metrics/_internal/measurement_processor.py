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
from dataclasses import replace
from typing import Callable, List, Optional

from opentelemetry.baggage import get_all
from opentelemetry.sdk.metrics._internal.measurement import Measurement
from opentelemetry.util.types import Attributes


class MeasurementProcessor(ABC):
    """Interface for processing measurements in a chain-of-responsibility pattern.

    MeasurementProcessor allows implementing custom processing logic for measurements
    including:
    - Dynamic injection of additional attributes based on Context
    - Dropping attributes
    - Dropping individual measurements
    - Modifying measurements

    Each processor in the chain is responsible for calling the next processor.
    """

    @abstractmethod
    def process(
        self,
        measurement: Measurement,
        next_processor: Callable[[Measurement], None],
    ) -> None:
        """Process a measurement and optionally call the next processor in the chain.

        Args:
            measurement: The measurement to process
            next_processor: Callable to invoke the next processor in the chain.
                          Processors MUST call this to continue the chain unless
                          they explicitly want to drop the measurement.
        """


class MeasurementProcessorChain:
    """Manages a chain of MeasurementProcessors.

    This class maintains a list of processors and provides a way to execute
    them in sequence using the chain-of-responsibility pattern.
    """

    def __init__(
        self, processors: Optional[List[MeasurementProcessor]] = None
    ):
        """Initialize the processor chain.

        Args:
            processors: List of processors to include in the chain.
                       If None or empty, uses NoOpMeasurementProcessor.
        """
        self._processors: List[MeasurementProcessor] = processors or []

    def process(
        self,
        measurement: Measurement,
        final_consumer: Callable[[Measurement], None],
    ) -> None:
        """Process a measurement through the entire chain.

        Args:
            measurement: The measurement to process
            final_consumer: The final consumer that will handle the measurement
                          after all processors have been applied
        """
        if not self._processors:
            final_consumer(measurement)
            return

        def create_next_step(index: int) -> Callable[[Measurement], None]:
            """Create the next step function for the processor at the given index."""
            if index >= len(self._processors):
                return final_consumer

            def next_step(processed_measurement: Measurement) -> None:
                if index + 1 < len(self._processors):
                    self._processors[index + 1].process(
                        processed_measurement, create_next_step(index + 1)
                    )
                else:
                    final_consumer(processed_measurement)

            return next_step

        # Start the chain with the first processor
        self._processors[0].process(measurement, create_next_step(0))


# Example implementations, should probably be moved to https://github.com/open-telemetry/opentelemetry-python-contrib
class BaggageMeasurementProcessor(MeasurementProcessor):
    """Processor that adds baggage values as measurement attributes.

    This processor extracts values from OpenTelemetry baggage and adds them
    as attributes to the measurement, enabling end-to-end telemetry correlation.
    """

    def __init__(self, baggage_keys: Optional[List[str]] = None):
        """Initialize the baggage processor.

        Args:
            baggage_keys: List of specific baggage keys to extract.
                         If None, extracts all baggage keys.
        """
        self._baggage_keys = baggage_keys

    def process(
        self,
        measurement: Measurement,
        next_processor: Callable[[Measurement], None],
    ) -> None:
        """Add baggage values as measurement attributes."""
        try:
            # Get all baggage from the measurement context
            baggage = get_all(measurement.context)

            if baggage:
                # Create new attributes by merging existing with baggage
                new_attributes = dict(measurement.attributes or {})

                for key, value in baggage.items():
                    # Filter by specific keys if provided
                    if self._baggage_keys is None or key in self._baggage_keys:
                        new_attributes[f"baggage.{key}"] = str(value)

                # Create a new measurement with updated attributes
                new_measurement = replace(
                    measurement, attributes=new_attributes
                )
                next_processor(new_measurement)
            else:
                # No baggage, pass through unchanged
                next_processor(measurement)
        except Exception:
            # On any error, pass through unchanged
            next_processor(measurement)


class AttributeFilterMeasurementProcessor(MeasurementProcessor):
    """Processor that filters out specific attributes from measurements."""

    def __init__(self, excluded_attributes: List[str]):
        """Initialize the attribute filter processor.

        Args:
            excluded_attributes: List of attribute keys to remove from measurements.
        """
        self._excluded_attributes = set(excluded_attributes)

    def process(
        self,
        measurement: Measurement,
        next_processor: Callable[[Measurement], None],
    ) -> None:
        """Remove specified attributes from the measurement."""
        if not measurement.attributes or not self._excluded_attributes:
            next_processor(measurement)
            return

        # Filter out excluded attributes
        new_attributes = {
            key: value
            for key, value in measurement.attributes.items()
            if key not in self._excluded_attributes
        }

        # Create a new measurement with filtered attributes
        new_measurement = replace(measurement, attributes=new_attributes)
        next_processor(new_measurement)


class StaticAttributeMeasurementProcessor(MeasurementProcessor):
    """Processor that adds static attributes to all measurements."""

    def __init__(self, static_attributes: Attributes):
        """Initialize the static attribute processor.

        Args:
            static_attributes: Dictionary of attributes to add to all measurements.
        """
        self._static_attributes = static_attributes or {}

    def process(
        self,
        measurement: Measurement,
        next_processor: Callable[[Measurement], None],
    ) -> None:
        """Add static attributes to the measurement."""
        if not self._static_attributes:
            next_processor(measurement)
            return

        # Create new attributes by merging existing with static attributes
        new_attributes = dict(measurement.attributes or {})
        new_attributes.update(self._static_attributes)

        # Create a new measurement with updated attributes
        new_measurement = replace(measurement, attributes=new_attributes)
        next_processor(new_measurement)
