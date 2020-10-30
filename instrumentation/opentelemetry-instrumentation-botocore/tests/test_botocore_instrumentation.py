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

from unittest.mock import Mock, patch

import botocore.session
from botocore.exceptions import ParamValidationError
from moto import (  # pylint: disable=import-error
    mock_ec2,
    mock_kinesis,
    mock_kms,
    mock_lambda,
    mock_s3,
    mock_sqs,
    mock_sts,
)

from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
from opentelemetry.test.test_base import TestBase


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
        self.assertEqual(
            dict(span.attributes),
            {
                "aws.operation": "DescribeInstances",
                "aws.region": "us-west-2",
                "aws.service": "ec2",
                "http.status_code": 200,
            },
        )
        self.assertEqual(span.name, "ec2")

    @mock_ec2
    def test_not_recording(self):
        mock_tracer = Mock()
        mock_span = Mock()
        mock_span.is_recording.return_value = False
        mock_tracer.start_span.return_value = mock_span
        mock_tracer.use_span.return_value.__enter__ = mock_span
        mock_tracer.use_span.return_value.__exit__ = True
        with patch("opentelemetry.trace.get_tracer") as tracer:
            tracer.return_value = mock_tracer
            ec2 = self.session.create_client("ec2", region_name="us-west-2")
            ec2.describe_instances()
            self.assertFalse(mock_span.is_recording())
            self.assertTrue(mock_span.is_recording.called)
            self.assertFalse(mock_span.set_attribute.called)
            self.assertFalse(mock_span.set_status.called)

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
        self.assertEqual(
            dict(span.attributes),
            {
                "aws.operation": "ListBuckets",
                "aws.region": "us-west-2",
                "aws.service": "s3",
                "http.status_code": 200,
            },
        )

        # testing for span error
        self.memory_exporter.get_finished_spans()
        with self.assertRaises(ParamValidationError):
            s3.list_objects(bucket="mybucket")
        spans = self.memory_exporter.get_finished_spans()
        assert spans
        span = spans[2]
        self.assertEqual(
            dict(span.attributes),
            {
                "aws.operation": "ListObjects",
                "aws.region": "us-west-2",
                "aws.service": "s3",
            },
        )

    # Comment test for issue 1088
    @mock_s3
    def test_s3_put(self):
        params = dict(Key="foo", Bucket="mybucket", Body=b"bar")
        s3 = self.session.create_client("s3", region_name="us-west-2")
        location = {"LocationConstraint": "us-west-2"}
        s3.create_bucket(Bucket="mybucket", CreateBucketConfiguration=location)
        s3.put_object(**params)

        spans = self.memory_exporter.get_finished_spans()
        assert spans
        self.assertEqual(len(spans), 2)
        self.assertEqual(
            spans[0].attributes,
            {
                "aws.operation": "CreateBucket",
                "aws.region": "us-west-2",
                "aws.service": "s3",
                "http.status_code": 200,
            },
        )
        self.assertEqual(
            spans[1].attributes,
            {
                "aws.operation": "PutObject",
                "aws.region": "us-west-2",
                "aws.service": "s3",
                "http.status_code": 200,
            },
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
        self.assertEqual(
            dict(span.attributes),
            {
                "aws.operation": "ListQueues",
                "aws.region": "us-east-1",
                "aws.service": "sqs",
                "http.status_code": 200,
            },
        )

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
        self.assertEqual(
            dict(span.attributes),
            {
                "aws.operation": "ListStreams",
                "aws.region": "us-east-1",
                "aws.service": "kinesis",
                "http.status_code": 200,
            },
        )

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
        self.assertEqual(
            dict(span.attributes),
            {
                "aws.operation": "ListFunctions",
                "aws.region": "us-east-1",
                "aws.service": "lambda",
                "http.status_code": 200,
            },
        )

    @mock_kms
    def test_kms_client(self):
        kms = self.session.create_client("kms", region_name="us-east-1")

        kms.list_keys(Limit=21)

        spans = self.memory_exporter.get_finished_spans()
        assert spans
        span = spans[0]
        self.assertEqual(len(spans), 1)
        self.assertEqual(
            dict(span.attributes),
            {
                "aws.operation": "ListKeys",
                "aws.region": "us-east-1",
                "aws.service": "kms",
                "http.status_code": 200,
            },
        )

        # checking for protection on kms against security leak
        self.assertTrue("params" not in span.attributes.keys())

    @mock_sts
    def test_sts_client(self):
        sts = self.session.create_client("sts", region_name="us-east-1")

        sts.get_caller_identity()

        spans = self.memory_exporter.get_finished_spans()
        assert spans
        span = spans[0]
        self.assertEqual(len(spans), 1)
        self.assertEqual(
            dict(span.attributes),
            {
                "aws.operation": "GetCallerIdentity",
                "aws.region": "us-east-1",
                "aws.service": "sts",
                "http.status_code": 200,
            },
        )

        # checking for protection on sts against security leak
        self.assertTrue("params" not in span.attributes.keys())
