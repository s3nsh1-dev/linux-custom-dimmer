"""Disposable, windowless service payload. systemd supplies the outer deadline."""

import os
import signal
import subprocess
import sys

signal.signal(signal.SIGTERM, signal.SIG_IGN)
child = subprocess.Popen(["/usr/bin/sleep", "30"])
print(f"dummy={os.getpid()} child={child.pid}", flush=True)
signal.alarm(25)
if "--freeze" in sys.argv:
    os.kill(os.getpid(), signal.SIGSTOP)
while True:
    signal.pause()
