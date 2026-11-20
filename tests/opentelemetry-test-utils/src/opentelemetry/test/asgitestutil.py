# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""``TestBase`` subclasses that drive an ASGI application through ``asgiref``.

An ASGI application is a coroutine taking a scope dict and a pair of ``receive``
and ``send`` callables, so a test has to build the scope, feed messages in and
collect messages out. ``asgiref.testing.ApplicationCommunicator`` does that
bookkeeping; the classes here hold one, supply a default HTTP scope and expose
the send and receive steps as methods.

Pick :class:`AsyncAsgiTestBase` for new tests: it inherits
``unittest.IsolatedAsyncioTestCase``, so its test methods are coroutines that
the runner awaits directly. :class:`AsgiTestBase` is the older form, whose test
methods are ordinary functions that drive the event loop themselves.
"""

import asyncio
from unittest import IsolatedAsyncioTestCase

from asgiref.testing import ApplicationCommunicator

from opentelemetry.test.test_base import TestBase


def setup_testing_defaults(scope):
    """Fill an ASGI scope with the fields of a plain ``GET /`` over HTTP.

    Named after ``wsgiref.util.setup_testing_defaults``, and like it, this
    updates the mapping in place and returns nothing. Keys the mapping already
    carries are overwritten, so set the fields a test cares about after calling
    this rather than before.

    Args:
        scope: The connection scope to fill. It gains ``client``, ``headers``,
            ``http_version``, ``method``, ``path``, ``query_string``,
            ``scheme``, ``server`` and ``type``. The defaults describe an
            HTTP/1.0 ``GET /`` from ``127.0.0.1`` with no headers and no query
            string. Fields an ASGI server would also set, ``asgi`` and
            ``root_path`` among them, are not added.
    """
    scope.update(
        {
            "client": ("127.0.0.1", 32767),
            "headers": [],
            "http_version": "1.0",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "scheme": "http",
            "server": ("127.0.0.1", 80),
            "type": "http",
        }
    )


class AsgiTestBase(TestBase):
    """Base class for a synchronous test that drives an ASGI application.

    Test methods are ordinary functions, and each call into the application
    runs the event loop to completion through
    ``asyncio.get_event_loop().run_until_complete``. Prefer
    :class:`AsyncAsgiTestBase` in new code, whose test methods are coroutines.

    Call ``seed_app`` with the application first, then ``send_input`` or
    ``send_default_request``, then ``get_output`` or ``get_all_output``.
    ``self.scope`` is the scope the application will see. The communicator
    keeps a reference to it and does not start the application, which begins on
    the first ``send_input`` or ``get_output``, so an edit made any time before
    that first call still reaches the application.

    ``tearDown`` waits up to one second for the application to finish and
    cancels it after that, and it does not call ``TestBase.tearDown``, so the
    trace and metrics globals this class installed stay installed until the next
    ``setUp`` replaces them.
    """

    def setUp(self):
        """Install the in-memory pipelines and build a default HTTP scope.

        Leaves ``self.communicator`` as ``None``: there is no application until
        ``seed_app`` is called.
        """
        super().setUp()

        self.scope = {}
        setup_testing_defaults(self.scope)
        self.communicator = None

    def tearDown(self):
        """Wait up to one second for the seeded application to finish.

        Waiting surfaces an exception the application raised after the last
        message a test read, which would otherwise be swallowed. One second is
        the default of ``ApplicationCommunicator.wait`` and this call does not
        override it, so an application still running when that second expires
        is cancelled rather than awaited, and a test that leaves one running
        pays the full second. This override does not call
        ``super().tearDown()``, so the trace and metrics globals are not reset
        here.
        """
        if self.communicator:
            asyncio.get_event_loop().run_until_complete(self.communicator.wait())

    def seed_app(self, app):
        """Attach an ASGI application to the scope built by ``setUp``.

        Call this once per test. Calling it again replaces the communicator and
        abandons the previous application without waiting for it.

        Args:
            app: The ASGI application to drive. The communicator is given a
                reference to ``self.scope`` and does not instantiate the
                application here: that happens on the first ``send_input`` or
                ``get_output``, so an edit to ``self.scope`` made before that
                first call does reach the application.
        """
        self.communicator = ApplicationCommunicator(app, self.scope)

    def send_input(self, message):
        """Send one ASGI message to the application and run the loop.

        Args:
            message: The message to deliver, for example
                ``{"type": "http.request", "body": b""}``. Its ``type`` has to
                be one the application expects for the scope type.
        """
        asyncio.get_event_loop().run_until_complete(self.communicator.send_input(message))

    def send_default_request(self):
        """Send an ``http.request`` message with an empty body.

        This is the one message a plain ``GET`` needs, since the absence of
        ``more_body`` tells the application the body is complete.
        """
        self.send_input({"type": "http.request", "body": b""})

    def get_output(self):
        """Take the next message the application sent.

        Returns:
            The next ASGI message, for example an ``http.response.start``.

        Raises:
            asyncio.TimeoutError: When no message is already queued. The wait
                is zero seconds, so this reads what the application has
                produced rather than waiting for it to produce more. A read
                that times out also cancels the application when it has not
                finished, so this ends the conversation rather than pausing it.
        """
        output = asyncio.get_event_loop().run_until_complete(self.communicator.receive_output(0))
        return output

    def get_all_output(self):
        """Take every message the application has already sent.

        Returns:
            A list of ASGI messages, in the order the application sent them,
            emptied out until nothing is queued. An application that has sent
            nothing yields an empty list rather than an error. Draining ends
            with a read that times out, which cancels an application that has
            not finished, so do not drain one that still has input to receive.
        """
        outputs = []
        while True:
            try:
                outputs.append(self.get_output())
            except asyncio.TimeoutError:
                break
        return outputs


class AsyncAsgiTestBase(TestBase, IsolatedAsyncioTestCase):
    """Base class for a test whose methods are coroutines.

    Same shape as :class:`AsgiTestBase`, but ``send_input``,
    ``send_default_request``, ``get_output`` and ``get_all_output`` are
    coroutines that a test method awaits, and ``IsolatedAsyncioTestCase`` runs
    each test method on its own event loop. Prefer this class in new code.

    ``tearDown`` has the same limit as in :class:`AsgiTestBase`: it does not
    call ``TestBase.tearDown``, so the trace and metrics globals are not reset.
    It is also synchronous, and drives the loop with ``run_until_complete``
    rather than awaiting, so a subclass that needs cleanup it can await has to
    override ``asyncTearDown`` instead.
    """

    def setUp(self):
        """Install the in-memory pipelines and build a default HTTP scope."""
        super().setUp()

        self.scope = {}
        setup_testing_defaults(self.scope)
        self.communicator = None

    def tearDown(self):
        """Wait up to one second for the seeded application to finish.

        One second is the default of ``ApplicationCommunicator.wait``, which
        this call does not override, so an application still running when that
        second expires is cancelled rather than awaited. This override does not
        call ``super().tearDown()``, so the trace and metrics globals are not
        reset here.
        """
        if self.communicator:
            asyncio.get_event_loop().run_until_complete(self.communicator.wait())

    def seed_app(self, app):
        """Attach an ASGI application to the scope built by ``setUp``.

        Args:
            app: The ASGI application to drive. The communicator is given a
                reference to ``self.scope`` and does not instantiate the
                application here: that happens on the first ``send_input`` or
                ``get_output``, so an edit to ``self.scope`` made before that
                first call does reach the application.
        """
        self.communicator = ApplicationCommunicator(app, self.scope)

    async def send_input(self, message):
        """Send one ASGI message to the application.

        Args:
            message: The message to deliver, for example
                ``{"type": "http.request", "body": b""}``.
        """
        await self.communicator.send_input(message)

    async def send_default_request(self):
        """Send an ``http.request`` message with an empty body."""
        await self.send_input({"type": "http.request", "body": b""})

    async def get_output(self, timeout=0.01):
        """Wait for the next message the application sends.

        Args:
            timeout: Seconds to wait for a message before giving up.

        Returns:
            The next ASGI message.

        Raises:
            asyncio.TimeoutError: When no message arrives within ``timeout``.
                The timed-out read also cancels the application when it has not
                finished, so this ends the conversation rather than pausing it.
        """
        return await self.communicator.receive_output(timeout)

    async def get_all_output(self, timeout=0.01):
        """Collect every message the application sends, then cancel it.

        Args:
            timeout: Seconds to wait for each further message. The call takes
                at least this long, because it ends by waiting for a message
                that never arrives.

        Returns:
            A list of ASGI messages in the order the application sent them.
            An application that sends nothing yields an empty list. The read
            that ends the loop cancels an application that has not finished, so
            do not drain one that still has input to receive.
        """
        outputs = []
        while True:
            try:
                outputs.append(await self.communicator.receive_output(timeout))
            except asyncio.TimeoutError:
                break
        return outputs
