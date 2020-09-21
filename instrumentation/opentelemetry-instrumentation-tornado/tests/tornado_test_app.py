# pylint: disable=W0223,R0201

import tornado.web
from tornado import gen


class AsyncHandler(tornado.web.RequestHandler):
    async def get(self):
        with self.application.tracer.start_as_current_span("sub-task-wrapper"):
            await self.do_something1()
            await self.do_something2()
            self.set_status(201)
            self.write("{}")

    async def do_something1(self):
        with self.application.tracer.start_as_current_span("sub-task-1"):
            tornado.gen.sleep(0.1)

    async def do_something2(self):
        with self.application.tracer.start_as_current_span("sub-task-2"):
            tornado.gen.sleep(0.1)


class CoroutineHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        with self.application.tracer.start_as_current_span("sub-task-wrapper"):
            yield self.do_something1()
            yield self.do_something2()
            self.set_status(201)
            self.write("{}")

    @gen.coroutine
    def do_something1(self):
        with self.application.tracer.start_as_current_span("sub-task-1"):
            tornado.gen.sleep(0.1)

    @gen.coroutine
    def do_something2(self):
        with self.application.tracer.start_as_current_span("sub-task-2"):
            tornado.gen.sleep(0.1)


class MainHandler(tornado.web.RequestHandler):
    def _handler(self):
        with self.application.tracer.start_as_current_span("manual"):
            self.write("Hello, world")
            self.set_status(201)

    def get(self):
        return self._handler()

    def post(self):
        return self._handler()

    def patch(self):
        return self._handler()

    def delete(self):
        return self._handler()

    def put(self):
        return self._handler()

    def head(self):
        return self._handler()

    def options(self):
        return self._handler()


class BadHandler(tornado.web.RequestHandler):
    def get(self):
        raise NameError("some random name error")


class DynamicHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_status(202)


class HealthCheckHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_status(200)


def make_app(tracer):
    app = tornado.web.Application(
        [
            (r"/", MainHandler),
            (r"/error", BadHandler),
            (r"/cor", CoroutineHandler),
            (r"/async", AsyncHandler),
            (r"/healthz", HealthCheckHandler),
            (r"/ping", HealthCheckHandler),
        ]
    )
    app.tracer = tracer
    return app
