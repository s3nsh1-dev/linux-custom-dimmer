"""Independent cleanup of each resource acquired by opt-in desktop tests."""

import subprocess
from contextlib import ExitStack, contextmanager


def refresh_cache():
    subprocess.run(
        ["kbuildsycoca6", "--noincremental"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


@contextmanager
def temporary_desktop(desktop, contents, connect, refresh=refresh_cache):
    desktop.parent.mkdir(parents=True, exist_ok=True)
    with ExitStack() as cleanup:
        stream = desktop.open("x")
        # LIFO: unregister, unlink, refresh. Every callback runs even if another
        # raises; ExitStack preserves the exception chain instead of hiding it.
        cleanup.callback(refresh)
        cleanup.callback(desktop.unlink, missing_ok=True)
        with stream:
            stream.write(contents)
        manager = connect()
        cleanup.callback(manager.unregister, desktop.name, "_launch")
        yield manager


@contextmanager
def sentinel_process():
    process = subprocess.Popen(["/usr/bin/sleep", "30"])
    try:
        yield process
    finally:
        process.terminate()
        process.wait(timeout=3)
