"""Installer command capture is bounded even when a command floods or hangs."""
import contextlib
import importlib.util
import io
import json
import os
import pty
import select
import signal
import tempfile
import time
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("setup_command_review", ROOT / "tools/setup.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class SetupCommandTests(unittest.TestCase):
    def assert_stopped(self, child):
        deadline = time.monotonic() + 0.5
        while True:
            try:
                state = Path("/proc", str(child), "stat").read_text().rsplit(")", 1)[1].split()[0]
            except FileNotFoundError:
                state = "gone"
            if state in ("Z", "gone") or time.monotonic() >= deadline:
                self.assertIn(state, ("Z", "gone"))
                return
            # SIGKILL applies to the group at once; the kernel can expose R
            # briefly before each orphan finishes its exit path.
            time.sleep(0.005)

    def run_command(self, code, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return setup.command([sys.executable, "-c", code], capture=True, **kwargs)

    def test_allowed_nonzero_preserves_dependency_list(self):
        output = self.run_command("import sys; print('cmake'); sys.exit(127)", allowed=(0, 127))
        self.assertEqual(output, "cmake\n")

    def test_offline_manager_child_has_no_compositor_signature(self):
        with patch.dict(os.environ, HYPRLAND_INSTANCE_SIGNATURE="do-not-contact-live-session"):
            code = "import os,json; print(json.dumps([os.getenv('HYPRLAND_INSTANCE_SIGNATURE'),os.getenv('XDG_RUNTIME_DIR')]))"
            expected_runtime = os.environ.get("XDG_RUNTIME_DIR")
            self.assertEqual(json.loads(self.run_command(code, compositor=False)), [None, expected_runtime])
            self.assertEqual(json.loads(self.run_command(code)), ["do-not-contact-live-session", expected_runtime])
            self.assertEqual(os.environ["HYPRLAND_INSTANCE_SIGNATURE"], "do-not-contact-live-session")

    def test_stdout_flood_without_newline_is_refused(self):
        with self.assertRaisesRegex(setup.files.Refused, "oversized"):
            self.run_command("import os,time; os.write(1,b'x'*200000); time.sleep(60)", timeout=2)

    def test_hung_capture_is_killed_and_reaped(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            self.run_command("import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)", timeout=0.1)

    def test_timeout_kills_parent_and_grandchild_for_captured_and_build_commands(self):
        with tempfile.TemporaryDirectory(prefix="hyprveil-command-tree-") as folder:
            for capture in (True, False):
                child_file = Path(folder) / str(capture)
                code = ("import os,pathlib,time; "
                        "child=os.fork(); "
                        "pathlib.Path(" + repr(str(child_file)) + ").write_text(str(os.getpid())) if child==0 else None; "
                        "time.sleep(60)")
                with self.subTest(capture=capture), contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(subprocess.TimeoutExpired):
                        setup.command([sys.executable, "-c", code], capture=capture, timeout=0.2)
                    child = int(child_file.read_text())
                    self.assert_stopped(child)

    def test_keyboard_interrupt_kills_the_owned_build_group(self):
        with tempfile.TemporaryDirectory(prefix="hyprveil-command-interrupt-") as folder:
            child_file = Path(folder) / "child"
            code = ("import os,pathlib,time; child=os.fork(); "
                    "pathlib.Path(" + repr(str(child_file)) + ").write_text(str(os.getpid())) if child==0 else None; time.sleep(60)")
            def interrupt(signum, frame):
                raise KeyboardInterrupt
            previous = signal.signal(signal.SIGALRM, interrupt)
            signal.setitimer(signal.ITIMER_REAL, 0.2)
            try:
                with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(KeyboardInterrupt):
                    setup.command([sys.executable, "-c", code], timeout=60)
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, previous)
            child = int(child_file.read_text())
            self.assert_stopped(child)

    def test_interactive_child_gets_terminal_and_parent_recovers_it(self):
        pid, terminal = pty.fork()
        if pid == 0:
            try:
                code = ("import os; assert os.tcgetpgrp(0)==os.getpgrp(); "
                        "print('TTY_READY',flush=True); assert input()=='accept'; print('TTY_CHILD_OK',flush=True)")
                setup.command([sys.executable, "-c", code], timeout=2)
                assert os.tcgetpgrp(0) == os.getpgrp()
                os.write(1, b"TTY_PARENT_OK\n")
                os._exit(0)
            except BaseException as error:
                os.write(1, ("TTY_FAILURE: " + repr(error) + "\n").encode())
                os._exit(1)
        output, sent, reaped = b"", False, False
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if select.select([terminal], [], [], 0.1)[0]:
                    try:
                        chunk = os.read(terminal, 8192)
                    except OSError:
                        break
                    if not chunk:
                        break
                    output += chunk
                    if b"TTY_READY" in output and not sent:
                        os.write(terminal, b"accept\n")
                        sent = True
                done, status = os.waitpid(pid, os.WNOHANG)
                if done:
                    reaped = True
                    # Drain final marker after the child exits.
                    while select.select([terminal], [], [], 0)[0]:
                        try:
                            chunk = os.read(terminal, 8192)
                        except OSError:
                            break
                        if not chunk: break
                        output += chunk
                    self.assertEqual(os.waitstatus_to_exitcode(status), 0, output.decode())
                    break
            self.assertIn(b"TTY_CHILD_OK", output, output.decode())
            self.assertIn(b"TTY_PARENT_OK", output, output.decode())
        finally:
            if not reaped:
                try: os.kill(pid, signal.SIGKILL)
                except ProcessLookupError: pass
                os.waitpid(pid, 0)
            os.close(terminal)

    def test_failed_command_carries_bounded_stderr(self):
        with self.assertRaises(subprocess.CalledProcessError) as error:
            self.run_command("import sys; print('specific failure',file=sys.stderr); sys.exit(2)")
        self.assertIn("specific failure", error.exception.stderr)


if __name__ == "__main__":
    unittest.main()
