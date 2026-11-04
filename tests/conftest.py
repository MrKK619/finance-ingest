import asyncio.proactor_events as pe
import signal


class _SandboxSelfPipeSock:
    """Stub socket to bypass Windows AppContainer loopback block during unit tests."""

    def fileno(self) -> int:
        return -1

    def close(self) -> None:
        pass

    def send(self, data: bytes) -> int:
        return len(data)

    def setblocking(self, flag: bool) -> None:
        pass


def _sandbox_make_self_pipe(self) -> None:
    self._ssock = _SandboxSelfPipeSock()
    self._csock = _SandboxSelfPipeSock()
    self._internal_fds += 1


def _sandbox_close_self_pipe(self) -> None:
    self._ssock = None
    self._csock = None
    self._internal_fds -= 1


pe.BaseProactorEventLoop._make_self_pipe = _sandbox_make_self_pipe
pe.BaseProactorEventLoop._close_self_pipe = _sandbox_close_self_pipe
pe.BaseProactorEventLoop._write_to_self = lambda self: None
pe.BaseProactorEventLoop._loop_self_reading = lambda self, f=None: None
signal.set_wakeup_fd = lambda fd, **kw: -1

