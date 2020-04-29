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

import os

import celery
from celery import Celery
from celery.exceptions import Retry

from opentelemetry.ext.celery import CeleryInstrumentor
from opentelemetry.sdk import resources
from opentelemetry.test.test_base import TestBase
from opentelemetry.trace.status import StatusCanonicalCode

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT ", "6379"))
REDIS_URL = "redis://{host}:{port}".format(host=REDIS_HOST, port=REDIS_PORT)
BROKER_URL = "{redis}/{db}".format(redis=REDIS_URL, db=0)
BACKEND_URL = "{redis}/{db}".format(redis=REDIS_URL, db=1)


class MyException(Exception):
    pass


class TestCeleryIntegration(TestBase):
    def setUp(self):
        super().setUp()
        CeleryInstrumentor().instrument()
        self.app = Celery(
            "celery.test_app", broker=BROKER_URL, backend=BACKEND_URL
        )

    def tearDown(self):
        with self.disable_logging():
            CeleryInstrumentor().uninstrument()
        super().tearDown()

    def test_concurrent_delays(self):
        # it should create one trace for each delayed execution
        @self.app.task
        def fn_task():
            return 42

        for x in range(100):
            fn_task.delay()

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 100)

    def test_fn_task_run(self):
        # the body of the function is not instrumented so calling it
        # directly doesn't create a trace
        @self.app.task
        def fn_task():
            return 42

        t = fn_task.run()
        self.assertEqual(t, 42)

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 0)

    def test_fn_task_call(self):
        # the body of the function is not instrumented so calling it
        # directly doesn't create a trace
        @self.app.task
        def fn_task():
            return 42

        t = fn_task()
        self.assertEqual(t, 42)

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 0)

    def test_fn_task_apply(self):
        # it should execute a traced task with a returning value
        @self.app.task
        def fn_task():
            return 42

        t = fn_task.apply()
        self.assertTrue(t.successful())
        self.assertEqual(t.result, 42)

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)

        span = spans[0]

        self.assertTrue(span.status.is_ok)
        self.assertEqual(span.name, "celery.run")
        self.assertEqual(
            span.attributes.get("celery.task_name"),
            "test_celery_functional.fn_task",
        )
        self.assertEqual(span.attributes.get("celery.id"), t.task_id)
        self.assertEqual(span.attributes.get("celery.action"), "run")
        self.assertEqual(span.attributes.get("celery.state"), "SUCCESS")

    def test_fn_task_apply_bind(self):
        # it should execute a traced task with a returning value
        @self.app.task(bind=True)
        def fn_task(self):
            return self

        t = fn_task.apply()
        self.assertTrue(t.successful())
        self.assertIn("fn_task", t.result.name)

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)

        span = spans[0]

        self.assertTrue(span.status.is_ok)
        self.assertEqual(span.name, "celery.run")
        self.assertEqual(
            span.attributes.get("celery.task_name"),
            "test_celery_functional.fn_task",
        )
        self.assertEqual(span.attributes.get("celery.id"), t.task_id)
        self.assertEqual(span.attributes.get("celery.action"), "run")
        self.assertEqual(span.attributes.get("celery.state"), "SUCCESS")

    def test_fn_task_apply_async(self):
        # it should execute a traced async task that has parameters
        @self.app.task
        def fn_task_parameters(user, force_logout=False):
            return (user, force_logout)

        t = fn_task_parameters.apply_async(
            args=["user"], kwargs={"force_logout": True}
        )
        self.assertEqual("PENDING", t.status)

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)

        span = spans[0]

        self.assertTrue(span.status.is_ok)
        self.assertEqual(span.name, "celery.apply")
        self.assertEqual(
            span.attributes.get("celery.task_name"),
            "test_celery_functional.fn_task_parameters",
        )
        self.assertEqual(span.attributes.get("celery.id"), t.task_id)
        self.assertEqual(span.attributes.get("celery.action"), "apply_async")
        self.assertEqual(span.attributes.get("celery.routing_key"), "celery")

    def test_fn_task_delay(self):
        # using delay shorthand must preserve arguments
        @self.app.task
        def fn_task_parameters(user, force_logout=False):
            return (user, force_logout)

        t = fn_task_parameters.delay("user", force_logout=True)
        self.assertEqual(t.status, "PENDING")

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)

        span = spans[0]

        self.assertTrue(span.status.is_ok)
        self.assertEqual(span.name, "celery.apply")
        self.assertEqual(
            span.attributes.get("celery.task_name"),
            "test_celery_functional.fn_task_parameters",
        )
        self.assertEqual(span.attributes.get("celery.id"), t.task_id)
        self.assertEqual(span.attributes.get("celery.action"), "apply_async")
        self.assertEqual(span.attributes.get("celery.routing_key"), "celery")

    def test_fn_exception(self):
        # it should catch exceptions in task functions
        @self.app.task
        def fn_exception():
            raise Exception("Task class is failing")

        t = fn_exception.apply()
        self.assertTrue(t.failed())
        self.assertIn("Task class is failing", t.traceback)

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)

        span = spans[0]

        self.assertEqual(span.name, "celery.run")
        self.assertEqual(
            span.attributes.get("celery.task_name"),
            "test_celery_functional.fn_exception",
        )
        self.assertEqual(span.attributes.get("celery.id"), t.task_id)
        self.assertEqual(span.attributes.get("celery.action"), "run")
        self.assertEqual(span.attributes.get("celery.state"), "FAILURE")

        self.assertIs(span.status.canonical_code, StatusCanonicalCode.UNKNOWN)
        self.assertIn("Task class is failing", span.status.description)

    def test_fn_exception_expected(self):
        # it should catch exceptions in task functions
        @self.app.task(throws=(MyException,))
        def fn_exception():
            raise MyException("Task class is failing")

        t = fn_exception.apply()
        self.assertTrue(t.failed())
        self.assertIn("Task class is failing", t.traceback)

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)

        span = spans[0]

        self.assertEqual(span.name, "celery.run")
        self.assertEqual(
            span.attributes.get("celery.task_name"),
            "test_celery_functional.fn_exception",
        )
        self.assertEqual(span.attributes.get("celery.id"), t.task_id)
        self.assertEqual(span.attributes.get("celery.action"), "run")
        self.assertEqual(span.attributes.get("celery.state"), "FAILURE")

        self.assertTrue(span.status.is_ok)

    def test_fn_retry_exception(self):
        # it should not catch retry exceptions in task functions
        @self.app.task
        def fn_exception():
            raise Retry("Task class is being retried")

        t = fn_exception.apply()
        self.assertFalse(t.failed())
        self.assertIn("Task class is being retried", t.traceback)

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)

        span = spans[0]

        self.assertEqual(span.name, "celery.run")
        self.assertEqual(
            span.attributes.get("celery.task_name"),
            "test_celery_functional.fn_exception",
        )
        self.assertEqual(span.attributes.get("celery.id"), t.task_id)
        self.assertEqual(span.attributes.get("celery.action"), "run")
        self.assertEqual(span.attributes.get("celery.state"), "RETRY")

        # This type of retrying should not be marked as an exceptio
        self.assertTrue(span.status.is_ok)

    def test_class_task(self):
        # it should execute class based tasks with a returning value
        class BaseTask(self.app.Task):
            def run(self):
                return 42

        t = BaseTask()
        # register the Task class if it's available (required in Celery 4.0+)
        register_task = getattr(self.app, "register_task", None)
        if register_task is not None:
            register_task(t)

        r = t.apply()
        self.assertTrue(r.successful())
        self.assertEqual(r.result, 42)

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)

        span = spans[0]

        self.assertTrue(span.status.is_ok)
        self.assertEqual(span.name, "celery.run")
        self.assertEqual(
            span.attributes.get("celery.task_name"),
            "test_celery_functional.BaseTask",
        )
        self.assertEqual(span.attributes.get("celery.id"), r.task_id)
        self.assertEqual(span.attributes.get("celery.action"), "run")
        self.assertEqual(span.attributes.get("celery.state"), "SUCCESS")

    def test_class_task_exception(self):
        # it should catch exceptions in class based tasks
        class BaseTask(self.app.Task):
            def run(self):
                raise Exception("Task class is failing")

        t = BaseTask()
        # register the Task class if it's available (required in Celery 4.0+)
        register_task = getattr(self.app, "register_task", None)
        if register_task is not None:
            register_task(t)

        r = t.apply()
        self.assertTrue(r.failed())
        self.assertIn("Task class is failing", r.traceback)

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)

        span = spans[0]

        self.assertEqual(span.name, "celery.run")
        self.assertEqual(
            span.attributes.get("celery.task_name"),
            "test_celery_functional.BaseTask",
        )
        self.assertEqual(span.attributes.get("celery.id"), r.task_id)
        self.assertEqual(span.attributes.get("celery.action"), "run")
        self.assertEqual(span.attributes.get("celery.state"), "FAILURE")

        self.assertIs(span.status.canonical_code, StatusCanonicalCode.UNKNOWN)
        self.assertIn("Task class is failing", span.status.description)

    def test_class_task_exception_expected(self):
        # it should catch exceptions in class based tasks
        class BaseTask(self.app.Task):
            throws = (MyException,)

            def run(self):
                raise MyException("Task class is failing")

        t = BaseTask()
        # register the Task class if it's available (required in Celery 4.0+)
        register_task = getattr(self.app, "register_task", None)
        if register_task is not None:
            register_task(t)

        r = t.apply()
        self.assertTrue(r.failed())
        self.assertIn("Task class is failing", r.traceback)

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)

        span = spans[0]

        self.assertEqual(span.name, "celery.run")
        self.assertEqual(
            span.attributes.get("celery.task_name"),
            "test_celery_functional.BaseTask",
        )
        self.assertEqual(span.attributes.get("celery.id"), r.task_id)
        self.assertEqual(span.attributes.get("celery.action"), "run")
        self.assertEqual(span.attributes.get("celery.state"), "FAILURE")

        self.assertTrue(span.status.is_ok)

    def test_shared_task(self):
        # Ensure Django Shared Task are supported
        @celery.shared_task
        def add(x, y):
            return x + y

        res = add.apply([2, 2])
        self.assertEqual(res.result, 4)

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)

        span = spans[0]

        self.assertTrue(span.status.is_ok)
        self.assertEqual(span.name, "celery.run")
        self.assertEqual(
            span.attributes.get("celery.task_name"),
            "test_celery_functional.add",
        )
        self.assertEqual(span.attributes.get("celery.id"), res.task_id)
        self.assertEqual(span.attributes.get("celery.action"), "run")
        self.assertEqual(span.attributes.get("celery.state"), "SUCCESS")

    def test_apply_async_previous_style_tasks(self):
        # ensures apply_async is properly patched if Celery 1.0 style tasks
        # are used even in newer versions. This should extend support to
        # previous versions of Celery.
        class CelerySuperClass(celery.task.Task):
            abstract = True

            @classmethod
            def apply_async(cls, args=None, kwargs=None, **kwargs_):
                return super(CelerySuperClass, cls).apply_async(
                    args=args, kwargs=kwargs, **kwargs_
                )

            def run(self, *args, **kwargs):
                if "stop" in kwargs:
                    # avoid call loop
                    return
                CelerySubClass.apply_async(args=[], kwargs={"stop": True})

        class CelerySubClass(CelerySuperClass):
            pass

        t = CelerySubClass()
        res = t.apply()

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 2)

        span = spans[1]
        self.assertTrue(span.status.is_ok)
        self.assertEqual(span.name, "celery.run")
        self.assertEqual(
            span.attributes.get("celery.task_name"),
            "test_celery_functional.CelerySubClass",
        )
        self.assertEqual(span.attributes.get("celery.id"), res.task_id)
        self.assertEqual(span.attributes.get("celery.action"), "run")
        self.assertEqual(span.attributes.get("celery.state"), "SUCCESS")

        span = spans[0]
        self.assertTrue(span.status.is_ok)
        self.assertEqual(span.name, "celery.apply")
        self.assertEqual(
            span.attributes.get("celery.task_name"),
            "test_celery_functional.CelerySubClass",
        )
        self.assertEqual(span.attributes.get("celery.action"), "apply_async")

    def test_custom_tracer_provider(self):
        @self.app.task
        def fn_task():
            return 42

        resource = resources.Resource.create({})
        result = self.create_tracer_provider(resource=resource)
        tracer_provider, exporter = result

        CeleryInstrumentor().uninstrument()
        CeleryInstrumentor().instrument(tracer_provider=tracer_provider)

        fn_task.delay()

        spans_list = exporter.get_finished_spans()
        self.assertEqual(len(spans_list), 1)
        span = spans_list[0]

        self.assertIs(span.resource, resource)
