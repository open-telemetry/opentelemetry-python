from sklearn.ensemble import RandomForestClassifier

from opentelemetry.instrumentation.sklearn import SklearnInstrumentor
from opentelemetry.test.test_base import TestBase
from opentelemetry.trace import SpanKind

from .fixtures import pipeline, random_input


class TestSklearn(TestBase):
    def test_span_properties(self):
        """Test that we get all of the spans we expect."""
        model = pipeline()
        SklearnInstrumentor().instrument_estimator(estimator=model)

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

    def test_attrib_config(self):
        """Test that the attribute config makes spans on the decision trees."""
        model = pipeline()
        attrib_config = {RandomForestClassifier: ["estimators_"]}
        SklearnInstrumentor(
            recurse_attribs=attrib_config
        ).instrument_estimator(estimator=model)

        x_test = random_input()
        model.predict(x_test)

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 8 + model.steps[-1][-1].n_estimators)
