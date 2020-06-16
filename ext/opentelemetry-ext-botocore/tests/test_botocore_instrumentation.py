import botocore.session
from botocore.exceptions import ParamValidationError
from moto import (  # pylint: disable=import-error
    mock_ec2,
    mock_kinesis,
    mock_kms,
    mock_lambda,
    mock_s3,
    mock_sqs,
)

from opentelemetry.ext.botocore import BotocoreInstrumentor
from opentelemetry.test.test_base import TestBase


def assert_span_http_status_code(span, code):
    """Assert on the span"s "http.status_code" tag"""
    tag = span.attributes["http.status_code"]
    assert tag == code, "%r != %r" % (tag, code)


class TestBotocoreInstrumentor(TestBase):
    """Botocore integration testsuite"""

    def setUp(self):
        super().setUp()
        BotocoreInstrumentor().instrument()

        self.session = botocore.session.get_session()
        self.session.set_credentials(
            access_key="access-key", secret_key="secret-key"
        )

    def tearDown(self):
        super().tearDown()
        BotocoreInstrumentor().uninstrument()

    @mock_ec2
    def test_traced_client(self):
        ec2 = self.session.create_client("ec2", region_name="us-west-2")

        ec2.describe_instances()

        spans = self.memory_exporter.get_finished_spans()
        assert spans
        span = spans[0]
        self.assertEqual(len(spans), 1)
        self.assertEqual(span.attributes["aws.agent"], "botocore")
        self.assertEqual(span.attributes["aws.region"], "us-west-2")
        self.assertEqual(span.attributes["aws.operation"], "DescribeInstances")
        assert_span_http_status_code(span, 200)
        self.assertEqual(span.resource, "ec2.describeinstances")
        self.assertEqual(span.name, "ec2.command")

    @mock_ec2
    def test_traced_client_analytics(self):
        ec2 = self.session.create_client("ec2", region_name="us-west-2")
        ec2.describe_instances()

        spans = self.memory_exporter.get_finished_spans()
        assert spans

    @mock_s3
    def test_s3_client(self):
        s3 = self.session.create_client("s3", region_name="us-west-2")

        s3.list_buckets()
        s3.list_buckets()

        spans = self.memory_exporter.get_finished_spans()
        assert spans
        span = spans[0]
        self.assertEqual(len(spans), 2)
        self.assertEqual(span.attributes["aws.operation"], "ListBuckets")
        assert_span_http_status_code(span, 200)
        self.assertEqual(span.resource, "s3.listbuckets")

        # testing for span error
        self.memory_exporter.get_finished_spans()
        with self.assertRaises(ParamValidationError):
            s3.list_objects(bucket="mybucket")
        spans = self.memory_exporter.get_finished_spans()
        assert spans
        span = spans[2]
        self.assertEqual(span.resource, "s3.listobjects")

    @mock_s3
    def test_s3_put(self):
        params = dict(Key="foo", Bucket="mybucket", Body=b"bar")
        s3 = self.session.create_client("s3", region_name="us-west-2")
        s3.create_bucket(Bucket="mybucket")
        s3.put_object(**params)

        spans = self.memory_exporter.get_finished_spans()
        assert spans
        span = spans[0]
        self.assertEqual(len(spans), 2)
        self.assertEqual(span.attributes["aws.operation"], "CreateBucket")
        assert_span_http_status_code(span, 200)
        self.assertEqual(span.resource, "s3.createbucket")
        self.assertEqual(spans[1].attributes["aws.operation"], "PutObject")
        self.assertEqual(spans[1].resource, "s3.putobject")
        self.assertEqual(spans[1].attributes["params.Key"], str(params["Key"]))
        self.assertEqual(
            spans[1].attributes["params.Bucket"], str(params["Bucket"])
        )
        self.assertTrue("params.Body" not in spans[1].attributes.keys())

    @mock_sqs
    def test_sqs_client(self):
        sqs = self.session.create_client("sqs", region_name="us-east-1")

        sqs.list_queues()

        spans = self.memory_exporter.get_finished_spans()
        assert spans
        span = spans[0]
        self.assertEqual(len(spans), 1)
        self.assertEqual(span.attributes["aws.region"], "us-east-1")
        self.assertEqual(span.attributes["aws.operation"], "ListQueues")
        assert_span_http_status_code(span, 200)
        self.assertEqual(span.resource, "sqs.listqueues")

    @mock_kinesis
    def test_kinesis_client(self):
        kinesis = self.session.create_client(
            "kinesis", region_name="us-east-1"
        )

        kinesis.list_streams()

        spans = self.memory_exporter.get_finished_spans()
        assert spans
        span = spans[0]
        self.assertEqual(len(spans), 1)
        self.assertEqual(span.attributes["aws.region"], "us-east-1")
        self.assertEqual(span.attributes["aws.operation"], "ListStreams")
        assert_span_http_status_code(span, 200)
        self.assertEqual(span.resource, "kinesis.liststreams")

    @mock_kinesis
    def test_unpatch(self):
        kinesis = self.session.create_client(
            "kinesis", region_name="us-east-1"
        )

        BotocoreInstrumentor().uninstrument()

        kinesis.list_streams()
        spans = self.memory_exporter.get_finished_spans()
        assert not spans, spans

    @mock_sqs
    def test_double_patch(self):
        sqs = self.session.create_client("sqs", region_name="us-east-1")

        BotocoreInstrumentor().instrument()
        BotocoreInstrumentor().instrument()

        sqs.list_queues()

        spans = self.memory_exporter.get_finished_spans()
        assert spans
        self.assertEqual(len(spans), 1)

    @mock_lambda
    def test_lambda_client(self):
        lamb = self.session.create_client("lambda", region_name="us-east-1")

        lamb.list_functions()

        spans = self.memory_exporter.get_finished_spans()
        assert spans
        span = spans[0]
        self.assertEqual(len(spans), 1)
        self.assertEqual(span.attributes["aws.region"], "us-east-1")
        self.assertEqual(span.attributes["aws.operation"], "ListFunctions")
        assert_span_http_status_code(span, 200)
        self.assertEqual(span.resource, "lambda.listfunctions")

    @mock_kms
    def test_kms_client(self):
        kms = self.session.create_client("kms", region_name="us-east-1")

        kms.list_keys(Limit=21)

        spans = self.memory_exporter.get_finished_spans()
        assert spans
        span = spans[0]
        self.assertEqual(len(spans), 1)
        self.assertEqual(span.attributes["aws.region"], "us-east-1")
        self.assertEqual(span.attributes["aws.operation"], "ListKeys")
        assert_span_http_status_code(span, 200)
        self.assertEqual(span.resource, "kms.listkeys")

        # checking for protection on sts against security leak
        self.assertTrue("params" not in span.attributes.keys())
