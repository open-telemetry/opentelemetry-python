from sklearn.ensemble import RandomForestClassifier

from opentelemetry.instrumentation.sklearn import (
    DEFAULT_EXCLUDE_CLASSES,
    DEFAULT_METHODS,
    SklearnInstrumentor,
    get_base_estimators,
)
from opentelemetry.test.test_base import TestBase
from opentelemetry.trace import SpanKind

from .fixtures import pipeline, random_input


class TestSklearn(TestBase):
    def test_package_instrumentation(self):
        ski = SklearnInstrumentor()

        base_estimators = get_base_estimators(packages=["sklearn"])

        model = pipeline()

        ski.instrument()
        # assert instrumented
        for _, estimator in base_estimators.items():
            for method_name in DEFAULT_METHODS:
                if issubclass(estimator, tuple(DEFAULT_EXCLUDE_CLASSES)):
                    assert not hasattr(estimator, "_original_" + method_name)
                    continue
                class_attr = getattr(estimator, method_name, None)
                if isinstance(class_attr, property):
                    assert not hasattr(estimator, "_original_" + method_name)
                    continue
                if hasattr(estimator, method_name):
                    assert hasattr(estimator, "_original_" + method_name)

        x_test = random_input()

        model.predict(x_test)

        spans = self.memory_exporter.get_finished_spans()
        for span in spans:
            print(span)
        self.assertEqual(len(spans), 8)
        self.memory_exporter.clear()

        ski.uninstrument()
        # assert uninstrumented
        for _, estimator in base_estimators.items():
            for method_name in DEFAULT_METHODS:
                if issubclass(estimator, tuple(DEFAULT_EXCLUDE_CLASSES)):
                    assert not hasattr(estimator, "_original_" + method_name)
                    continue
                class_attr = getattr(estimator, method_name, None)
                if isinstance(class_attr, property):
                    assert not hasattr(estimator, "_original_" + method_name)
                    continue
                if hasattr(estimator, method_name):
                    assert not hasattr(estimator, "_original_" + method_name)

        model = pipeline()
        x_test = random_input()

        model.predict(x_test)

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 0)

    def test_span_properties(self):
        """Test that we get all of the spans we expect."""
        model = pipeline()
        ski = SklearnInstrumentor()
        ski.instrument_estimator(estimator=model)

        x_test = random_input()

        model.predict(x_test)

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 8)
        span = spans[0]
        self.assertEqual(span.name, "StandardScaler.transform")
        self.assertEqual(span.kind, SpanKind.INTERNAL)
        self.assertEqual(span.parent.span_id, spans[-1].context.span_id)
        span = spans[1]
        self.assertEqual(span.name, "Normalizer.transform")
        self.assertEqual(span.kind, SpanKind.INTERNAL)
        self.assertEqual(span.parent.span_id, spans[-1].context.span_id)
        span = spans[2]
        self.assertEqual(span.name, "PCA.transform")
        self.assertEqual(span.kind, SpanKind.INTERNAL)
        self.assertEqual(span.parent.span_id, spans[4].context.span_id)
        span = spans[3]
        self.assertEqual(span.name, "TruncatedSVD.transform")
        self.assertEqual(span.kind, SpanKind.INTERNAL)
        self.assertEqual(span.parent.span_id, spans[4].context.span_id)
        span = spans[4]
        self.assertEqual(span.name, "FeatureUnion.transform")
        self.assertEqual(span.kind, SpanKind.INTERNAL)
        self.assertEqual(span.parent.span_id, spans[-1].context.span_id)
        span = spans[5]
        self.assertEqual(span.name, "RandomForestClassifier.predict_proba")
        self.assertEqual(span.kind, SpanKind.INTERNAL)
        self.assertEqual(span.parent.span_id, spans[6].context.span_id)
        span = spans[6]
        self.assertEqual(span.name, "RandomForestClassifier.predict")
        self.assertEqual(span.kind, SpanKind.INTERNAL)
        self.assertEqual(span.parent.span_id, spans[-1].context.span_id)
        span = spans[7]
        self.assertEqual(span.name, "Pipeline.predict")
        self.assertEqual(span.kind, SpanKind.INTERNAL)

        self.memory_exporter.clear()

        # uninstrument
        ski.uninstrument_estimator(estimator=model)
        x_test = random_input()
        model.predict(x_test)
        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 0)

    def test_attrib_config(self):
        """Test that the attribute config makes spans on the decision trees."""
        model = pipeline()
        attrib_config = {RandomForestClassifier: ["estimators_"]}
        ski = SklearnInstrumentor(
            recurse_attribs=attrib_config,
            exclude_classes=[],  # decision trees excluded by default
        )
        ski.instrument_estimator(estimator=model)

        x_test = random_input()
        model.predict(x_test)

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 8 + model.steps[-1][-1].n_estimators)

        self.memory_exporter.clear()

        ski.uninstrument_estimator(estimator=model)
        x_test = random_input()
        model.predict(x_test)
        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 0)
