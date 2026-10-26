"""T002 private fixtures. No database, Docker, public routes or production flags.

Raw child stdout/stderr stay in mode-0600 files below a mode-0700 temporary
directory, outside published evidence. Only explicitly launched children are
terminated. A later QA collector must sanitize evidence before publishing it.
"""

import os
import subprocess
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.support.clock import FrozenClock
from tests.support.faults import Faults


class PrivateSubprocesses:
    """Launch isolated Python children; inherit no credentials or control inputs."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory
        self._children: list[subprocess.Popen[bytes]] = []
        self._closed = False

    def start(self, code: str) -> subprocess.Popen[bytes]:
        if self._closed:
            raise RuntimeError("fixture_subprocess_factory_closed")
        index = len(self._children)
        stdout = self._directory / f"child-{index}.stdout"
        stderr = self._directory / f"child-{index}.stderr"
        # Exclusive creation and permissions apply before a child can write.
        with (
            os.fdopen(os.open(stdout, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as out,
            os.fdopen(os.open(stderr, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as err,
        ):
            child = subprocess.Popen(
                # -I ignores PYTHON* variables, so choose packaged tzdata explicitly.
                [sys.executable, "-I", "-c", "import zoneinfo; zoneinfo.reset_tzpath(())\n" + code],
                cwd=self._directory,
                env={"PATH": os.defpath, "TZ": "UTC", "PYTHONTZPATH": ""},
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
            )
        self._children.append(child)
        return child

    def close(self) -> None:
        self._closed = True
        for child in reversed(self._children):
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=3)
            else:
                child.wait(timeout=3)


@pytest.fixture
def frozen_clock() -> FrozenClock:
    """Function-scoped time shared only through explicit dependency injection."""
    return FrozenClock(datetime(2030, 1, 1, tzinfo=UTC))


@pytest.fixture
def faults() -> Faults:
    return Faults()


@pytest.fixture
def private_runtime_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "runtime"
    directory.mkdir(mode=0o700)
    return directory


@pytest.fixture
def python_subprocess(private_runtime_dir: Path) -> Iterator[PrivateSubprocesses]:
    children = PrivateSubprocesses(private_runtime_dir)
    try:
        yield children
    finally:
        children.close()
