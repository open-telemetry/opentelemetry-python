import boto.ec2
import boto.s3
import boto.awslambda
import boto.sts
import boto.elasticache
from moto import (
    mock_s3_deprecated,
    mock_ec2_deprecated,
    mock_lambda_deprecated,
    mock_sts_deprecated
)

from opentelemetry.ext.boto import BotoInstrumentor
from opentelemetry.test.test_base import TestBase

# testing
from unittest import skipUnless


def assert_span_http_status_code(span, code):
    """Assert on the span's 'http.status_code' tag"""
    tag = span.attributes["http.status_code"]
    assert tag == code, "%r != %r" % (tag, code)


class TestBotoInstrumentor(TestBase):
    """Botocore integration testsuite"""

    TEST_SERVICE = "test-boto-tracing"

    def setUp(self):
        super().setUp()
        BotoInstrumentor().instrument()

    def tearDown(self):
        BotoInstrumentor().uninstrument()

    @mock_ec2_deprecated
    def test_ec2_client(self):
        ec2 = boto.ec2.connect_to_region("us-west-2")

        ec2.get_all_instances()

        spans = self.memory_exporter.get_finished_spans()
        assert spans
        self.assertEqual(len(spans), 1)
        span = spans[0]
        self.assertEqual(span.attributes["aws.operation"], "DescribeInstances")
        assert_span_http_status_code(span, 200)
        self.assertEqual(span.attributes["http.method"], "POST")
        self.assertEqual(span.attributes["aws.region"], "us-west-2")

        # Create an instance
        ec2.run_instances(21)
        spans = self.memory_exporter.get_finished_spans()
        assert spans
        self.assertEqual(len(spans), 2)
        span = spans[1]
        self.assertEqual(span.attributes["aws.operation"], "RunInstances")
        assert_span_http_status_code(span, 200)
        self.assertEqual(span.attributes["http.method"], "POST")
        self.assertEqual(span.attributes["aws.region"], "us-west-2")
        self.assertEqual(span.name, "ec2.command")

    @mock_ec2_deprecated
    def test_analytics_enabled_with_rate(self):
        ec2 = boto.ec2.connect_to_region("us-west-2")

        ec2.get_all_instances()

        spans = self.memory_exporter.get_finished_spans()
        assert spans

    @mock_ec2_deprecated
    def test_analytics_enabled_without_rate(self):
        ec2 = boto.ec2.connect_to_region("us-west-2")

        ec2.get_all_instances()

        spans = self.memory_exporter.get_finished_spans()
        assert spans

    @mock_s3_deprecated
    def test_s3_client(self):
        s3 = boto.s3.connect_to_region("us-east-1")

        s3.get_all_buckets()
        spans = self.memory_exporter.get_finished_spans()
        assert spans
        self.assertEqual(len(spans), 1)
        span = spans[0]
        assert_span_http_status_code(span, 200)
        self.assertEqual(span.attributes["http.method"], "GET")
        self.assertEqual(span.attributes["aws.operation"], "get_all_buckets")

        # Create a bucket command
        s3.create_bucket("cheese")
        spans = self.memory_exporter.get_finished_spans()
        assert spans
        self.assertEqual(len(spans), 2)
        span = spans[1]
        assert_span_http_status_code(span, 200)
        self.assertEqual(span.attributes["http.method"], "PUT")
        self.assertEqual(span.attributes["path"], "/")
        self.assertEqual(span.attributes["aws.operation"], "create_bucket")

        # Get the created bucket
        s3.get_bucket("cheese")
        spans = self.memory_exporter.get_finished_spans()
        assert spans
        self.assertEqual(len(spans), 3)
        span = spans[2]
        assert_span_http_status_code(span, 200)
        self.assertEqual(span.attributes["http.method"], "HEAD")
        self.assertEqual(span.attributes["aws.operation"], "head_bucket")
        self.assertEqual(span.name, "s3.command")

        # Checking for resource incase of error
        try:
            s3.get_bucket("big_bucket")
        except Exception:
            spans = self.memory_exporter.get_finished_spans()
            assert spans
            span = spans[0]
            self.assertEqual(span.resource, "s3.head")

    @mock_s3_deprecated
    def test_s3_put(self):
        s3 = boto.s3.connect_to_region("us-east-1")
        s3.create_bucket("mybucket")
        bucket = s3.get_bucket("mybucket")
        k = boto.s3.key.Key(bucket)
        k.key = "foo"
        k.set_contents_from_string("bar")

        spans = self.memory_exporter.get_finished_spans()
        assert spans
        # create bucket
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0].attributes["aws.operation"], "create_bucket")
        assert_span_http_status_code(spans[0], 200)
        # get bucket
        self.assertEqual(spans[1].attributes["aws.operation"], "head_bucket")
        self.assertEqual(spans[1].resource, "s3.head")
        # put object
        self.assertEqual(
            spans[2].attributes["aws.operation"], "_send_file_internal"
        )
        self.assertEqual(spans[2].resource, "s3.put")

    @mock_lambda_deprecated
    def test_unpatch(self):
        from boto.awslambda import connect_to_region
        lamb = connect_to_region("us-east-2")

        from opentelemetry.ext.boto import BotoInstrumentor
        BotoInstrumentor().uninstrument()

        # multiple calls
        lamb.list_functions()
        spans = self.memory_exporter.get_finished_spans()
        assert not spans, spans

    @mock_s3_deprecated
    def test_double_patch(self):
        from boto.s3 import connect_to_region
        s3 = connect_to_region("us-east-1")

        from opentelemetry.ext.boto import BotoInstrumentor
        BotoInstrumentor().instrument()
        BotoInstrumentor().instrument()

        # Get the created bucket
        s3.create_bucket("cheese")
        spans = self.memory_exporter.get_finished_spans()
        assert spans
        self.assertEqual(len(spans), 1)

    @mock_lambda_deprecated
    def test_lambda_client(self):
        from boto.awslambda import connect_to_region
        lamb = connect_to_region("us-east-2")

        # multiple calls
        lamb.list_functions()
        lamb.list_functions()

        spans = self.memory_exporter.get_finished_spans()
        assert spans
        self.assertEqual(len(spans), 2)
        span = spans[0]
        assert_span_http_status_code(span, 200)
        self.assertEqual(span.attributes["http.method"], "GET")
        self.assertEqual(span.attributes["aws.region"], "us-east-2")
        self.assertEqual(span.attributes["aws.operation"], "list_functions")

    @mock_sts_deprecated
    def test_sts_client(self):
        from boto.sts import connect_to_region
        sts = connect_to_region("us-west-2")

        sts.get_federation_token(12, duration=10)

        spans = self.memory_exporter.get_finished_spans()
        assert spans
        span = spans[0]
        self.assertEqual(span.attributes["aws.region"], "us-west-2")
        self.assertEqual(
            span.attributes["aws.operation"], "GetFederationToken"
        )

        # checking for protection on sts against security leak
        self.assertIsNone(span.attributes["args.path"])

    @skipUnless(
        False,
        (
            "Test to reproduce the case where args sent to patched function "
            "are None, can\"t be mocked: needs AWS crendentials"
        ),
    )
    def test_elasticache_client(self):
        from boto.elasticache import connect_to_region
        elasticache = connect_to_region("us-west-2")

        elasticache.describe_cache_clusters()

        spans = self.memory_exporter.get_finished_spans()
        assert spans
        span = spans[0]
        self.assertEqual(span.attributes["aws.region"], "us-west-2")

    """
    @mock_ec2_deprecated
    def test_ec2_client_ot(self):
        OpenTracing compatibility check of the test_ec2_client test.

        ec2 = boto.ec2.connect_to_region("us-west-2")

        ot_tracer = init_tracer("my_svc", self.tracer)
        writer = self.tracer.writer

        with ot_tracer.start_active_span("ot_span"):
            ec2.get_all_instances()
        spans = writer.pop()
        assert spans
        self.assertEqual(len(spans), 2)
        ot_span, dd_span = spans

        # confirm the parenting
        self.assertIsNone(ot_span.parent_id)
        self.assertEqual(dd_span.parent_id, ot_span.span_id)

        self.assertEqual(ot_span.resource, "ot_span")
        self.assertEqual(
            dd_span.attributes["aws.operation"), "DescribeInstances"
        )
        assert_span_http_status_code(dd_span, 200)
        self.assertEqual(dd_span.attributes["http.method"), "POST")
        self.assertEqual(dd_span.attributes["aws.region"), "us-west-2")

        with ot_tracer.start_active_span("ot_span"):
            ec2.run_instances(21)
        spans = writer.pop()
        assert spans
        self.assertEqual(len(spans), 2)
        ot_span, dd_span = spans

        # confirm the parenting
        self.assertIsNone(ot_span.parent_id)
        self.assertEqual(dd_span.parent_id, ot_span.span_id)

        self.assertEqual(dd_span.attributes["aws.operation"), "RunInstances")
        assert_span_http_status_code(dd_span, 200)
        self.assertEqual(dd_span.attributes["http.method"), "POST")
        self.assertEqual(dd_span.attributes["aws.region"), "us-west-2")
        self.assertEqual(dd_span.name, "ec2.command")
    """
