import abc
import threading
import typing


class TimerABC(abc.ABC):
    """
    An interface extracted from PeriodicTimer so alternative implementations can be used for testing.

    Implementations should execute the passed-in callback on a timer at the specified interval at a minimum. The
    callback can be run sooner than the interval via the poke() method, which also resets the timer.
    """

    @abc.abstractmethod
    def set_callback(self, cb) -> None:
        pass

    @abc.abstractmethod
    def start(self) -> None:
        pass

    @abc.abstractmethod
    def poke(self) -> None:
        pass

    @abc.abstractmethod
    def stop(self) -> None:
        pass


class ThreadBasedTimer(TimerABC):
    """
    A Timer implementation that uses a threading.Timer for each interval and runs the callback asynchronously using a
    new Thread on poke().
    """

    def __init__(self, interval_sec: int):
        self.interval_sec = interval_sec
        self.cb = lambda: None
        self.timer = None
        self.lock = threading.Lock()

    def set_callback(self, cb) -> None:
        with self.lock:
            self.cb = cb

    def start(self) -> None:
        with self.lock:
            self.timer = threading.Timer(self.interval_sec, self._work)
            self.timer.daemon = True
            self.timer.start()

    def _work(self):
        self.cb()
        self.start()

    def poke(self) -> None:
        with self.lock:
            self._do_stop()
            threading.Thread(target=self._work, daemon=True).start()

    def stop(self) -> None:
        with self.lock:
            self._do_stop()

    def _do_stop(self):
        if self.timer is None:
            return
        self.timer.cancel()
        self.timer = None


class EventBasedTimer(TimerABC):
    """
    Deprecated but left here for reference. I believe this implementation is unnecessarily complicated.
    """

    def __init__(
        self,
        interval_sec: int,
        callback: typing.Callable[[], None] = lambda: None,
        daemon: bool = True,
    ):
        self._interval_sec = interval_sec
        self._callback = callback
        self._daemon = daemon
        self._stop = threading.Event()
        self._poke = threading.Event()
        self._new_thread()

    def _new_thread(self):
        self._thread = threading.Thread(target=self._work, daemon=self._daemon)

    def set_callback(self, callback: typing.Callable[[], None]) -> None:
        self._callback = callback

    def start(self) -> None:
        self._thread.start()

    def _work(self) -> None:
        while True:
            self._poke.wait(timeout=self._interval_sec)
            if self._stop.is_set():
                break
            self._callback()

    def poke(self) -> None:
        """
        This method schedules the callback to be executed immediately instead of waiting for the next timeout. It also
        resets the timer.
        """
        self._poke.set()

    def stop(self) -> None:
        self._stop.set()
        self.poke()  # in case we're waiting for a poke timeout
        self._thread.join()
        self._new_thread()  # in case we want to start it again

    def started(self) -> bool:
        return self._thread.is_alive()

    def stopped(self) -> bool:
        return self._stop.is_set()


class ThreadlessTimer(TimerABC):
    """
    For testing/experimentation. Synchronously executes the callback when you call poke().
    """

    def __init__(self):
        self._cb = lambda: None

    def set_callback(self, cb):
        self._cb = cb

    def start(self):
        pass

    def poke(self):
        self._cb()

    def stop(self):
        pass

    def started(self) -> None:
        pass

    def stopped(self) -> None:
        pass
