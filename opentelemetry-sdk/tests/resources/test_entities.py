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

from unittest import TestCase
from unittest.mock import Mock, patch

from opentelemetry.sdk.resources import (
    Entity,
    EntityDetector,
    Resource,
    Type0EntityDetector,
    Type1EntityDetector,
    _get_entity_detectors,
    _select_entities,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


class TestEntities(TestCase):

    def test_get_entity_detectors(self):

        entity_detectors = _get_entity_detectors()

        self.assertEqual(len(entity_detectors), 2)

        self.assertIsInstance(entity_detectors[0], Type0EntityDetector)
        self.assertIsInstance(entity_detectors[1], Type1EntityDetector)

    def test_get_entity_detectors_same_priorities(self):
        class Type2EntityDetector(EntityDetector):

            _entity = None

            def detect(self) -> Entity:

                if self._entity is None:
                    self._entity = Entity(
                        "type0", id_={"a": "b"}, attributes={"c": "d"}
                    )

                return self._entity

            @property
            def priority(self):
                return 0

        with patch(
            "opentelemetry.sdk.resources.entry_points",
            return_value=[
                Mock(load=Mock(return_value=Type0EntityDetector)),
                Mock(load=Mock(return_value=Type1EntityDetector)),
                Mock(load=Mock(return_value=Type2EntityDetector)),
            ],
        ):

            with self.assertRaises(ValueError):
                _get_entity_detectors()

    def test_select_entities(self):

        unselected_entities = [
            Entity("type_0", {"a": "a"}, {"b": "b"}, "a"),
            Entity("type_0", {"a": "a"}, {"c": "c"}, "a"),
        ]

        selected_entities = _select_entities(unselected_entities)

        self.assertEqual(len(selected_entities), 1)
        self.assertEqual(selected_entities[0].type, "type_0")
        self.assertEqual(selected_entities[0].id, {"a": "a"})
        self.assertEqual(selected_entities[0].attributes, {"b": "b", "c": "c"})
        self.assertEqual(selected_entities[0].schema_url, "a")

        unselected_entities = [
            Entity("type_0", {"a": "a"}, {"b": "b"}, "a"),
            Entity("type_0", {"a": "a"}, {"c": "c"}, "b"),
        ]

        selected_entities = _select_entities(unselected_entities)

        self.assertEqual(len(selected_entities), 1)
        self.assertEqual(selected_entities[0].type, "type_0")
        self.assertEqual(selected_entities[0].id, {"a": "a"})
        self.assertEqual(selected_entities[0].attributes, {"b": "b"})
        self.assertEqual(selected_entities[0].schema_url, "a")

        unselected_entities = [
            Entity("type_0", {"a": "a"}, {"b": "b"}, "a"),
            Entity("type_0", {"a": "b"}, {"c": "c"}, "a"),
        ]

        selected_entities = _select_entities(unselected_entities)

        self.assertEqual(len(selected_entities), 1)
        self.assertEqual(selected_entities[0].type, "type_0")
        self.assertEqual(selected_entities[0].id, {"a": "a"})
        self.assertEqual(selected_entities[0].attributes, {"b": "b"})
        self.assertEqual(selected_entities[0].schema_url, "a")

        unselected_entities = [
            Entity("type_0", {"a": "a"}, {"b": "b"}, "a"),
            Entity("type_1", {"a": "b"}, {"c": "c"}, "a"),
        ]

        selected_entities = _select_entities(unselected_entities)

        self.assertEqual(len(selected_entities), 2)
        self.assertEqual(selected_entities[0].type, "type_0")
        self.assertEqual(selected_entities[0].id, {"a": "a"})
        self.assertEqual(selected_entities[0].attributes, {"b": "b"})
        self.assertEqual(selected_entities[0].schema_url, "a")

        self.assertEqual(selected_entities[1].type, "type_1")
        self.assertEqual(selected_entities[1].id, {"a": "b"})
        self.assertEqual(selected_entities[1].attributes, {"c": "c"})
        self.assertEqual(selected_entities[1].schema_url, "a")

    def test_create_using_entities(self):

        resource = Resource.create_using_entities()

        self.assertEqual(
            resource.attributes,
            {
                "telemetry.sdk.language": "python",
                "telemetry.sdk.name": "opentelemetry",
                "telemetry.sdk.version": "1.28.0.dev0",
                "a": "b",
                "c": "d",
                "service.name": "unknown_service",
            },
        )
        self.assertEqual(resource.schema_url, "")

    def test_export_entities(self):

        tracer_provider = TracerProvider(
            resource=Resource.create_using_entities()
        )

        tracer = tracer_provider.get_tracer(__name__)

        in_memory_exporter = InMemorySpanExporter()
        tracer_provider.add_span_processor(
            SimpleSpanProcessor(in_memory_exporter)
        )

        with tracer.start_as_current_span("a"):
            with tracer.start_as_current_span("b"):
                with tracer.start_as_current_span("c"):
                    pass

        for span in in_memory_exporter.get_finished_spans():
            self.assertEqual(
                span.resource.attributes,
                {
                    "telemetry.sdk.language": "python",
                    "telemetry.sdk.name": "opentelemetry",
                    "telemetry.sdk.version": "1.28.0.dev0",
                    "a": "b",
                    "c": "d",
                    "service.name": "unknown_service",
                },
            )
            self.assertEqual(span.resource.schema_url, "")
