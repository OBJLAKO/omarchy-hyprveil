#!/usr/bin/python3
"""Check privacy watcher admission, payload bounds and change-only output."""
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / "plugin/privacy-watch"
loader = importlib.machinery.SourceFileLoader("privacy_watch", str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
watch = importlib.util.module_from_spec(spec)
loader.exec_module(watch)


def state(kind="hidden", native=True, inherited=False):
    return {"state": kind, "address": "0xabc" if kind != "none" else "",
            "stable_id": "402653184" if kind != "none" else "",
            "native_private": native, "inherited": inherited}


class PayloadTests(unittest.TestCase):
    def test_only_consistent_minimal_atomic_states_are_accepted(self):
        for value in (state(), state(native=False, inherited=True), state("visible", False), state("none", False),
                      dict(state(), stable_id="18446744073709551615"), dict(state(), stable_id="10000000000000000000"),
                      dict(state(), stable_id="9007199254740993"), dict(state(), stable_id="1")):
            self.assertEqual(watch.validate_state(value), value)
        malformed = [dict(state(), title="private title"), dict(state(), **{"class": "private app"}),
            state(native=False), state(inherited=True), state("visible"), state("none"),
            dict(state(), native_private=1), dict(state(), address="0x0"),
            dict(state(), address="0xABC"), dict(state(), address="0x" + "a" * 17), watch.UNKNOWN,
            dict(state(), stable_id=""), dict(state(), stable_id=402653184), dict(state(), stable_id="0"),
            dict(state(), stable_id="01"), dict(state(), stable_id="1" * 21), dict(state(), stable_id="123\n"),
            dict(state(), stable_id="18446744073709551616"), dict(state(), stable_id="9" * 20),
            dict(state(), stable_id="1e5"), dict(state(), stable_id="-1")]
        for value in malformed:
            with self.subTest(value=value), self.assertRaises(watch.Refused):
                watch.validate_state(value)

    def test_duplicate_keys_are_rejected(self):
        with self.assertRaises(watch.Refused):
            json.loads('{"state":"hidden","state":"visible"}', object_pairs_hook=watch.unique_object)

    def test_signature_cannot_be_path_or_argument_injection(self):
        self.assertEqual(watch.validate_signature("synthetic_instance_123"), "synthetic_instance_123")
        for value in ("", ".", "..", "../abc", "-i abc", "a\nb", "a" * 161, "абв", None):
            with self.subTest(value=value), self.assertRaises(watch.Refused):
                watch.validate_signature(value)

    def test_event_payload_is_not_retained_or_emitted(self):
        parser = watch.EventWakeup()
        self.assertFalse(parser.feed(b"windowtitle>>private"))
        self.assertTrue(parser.feed(b" title\nactivewindow>>another private title\n"))
        self.assertEqual(parser.__dict__, {"partial": 0})
        parser.feed(b"x" * 4096)
        for _ in range(15):
            parser.feed(b"x" * 4096)
        with self.assertRaises(watch.Refused):
            parser.feed(b"x")

    def test_change_only_output_and_unknown_has_no_title(self):
        output = io.StringIO()
        emitter = watch.Emitter()
        with contextlib.redirect_stdout(output):
            emitter.emit(state())
            emitter.emit(state())
            emitter.emit(watch.UNKNOWN)
            emitter.emit(watch.UNKNOWN)
        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual([json.loads(line) for line in lines], [state(), watch.UNKNOWN])

    def test_reused_address_with_new_stable_id_emits_new_identity(self):
        output = io.StringIO()
        emitter = watch.Emitter()
        with contextlib.redirect_stdout(output):
            emitter.emit(state())
            emitter.emit(dict(state(), stable_id="402653185"))
        self.assertEqual(len(output.getvalue().splitlines()), 2)

    def test_restricted_environment_discards_inherited_injection(self):
        with mock.patch.dict(os.environ, {"LD_PRELOAD": "bad", "PATH": "/tmp", "HOME": "/tmp"}):
            value = watch.fixed_env(Path("/run/user/1000"), "abc")
        self.assertEqual(set(value), {"PATH", "HOME", "LANG", "XDG_RUNTIME_DIR", "HYPRLAND_INSTANCE_SIGNATURE"})
        self.assertEqual(value["PATH"], "/usr/bin:/bin")
        self.assertNotEqual(value["HOME"], "/tmp")


class SocketTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="privacy-watch-test-")
        self.addCleanup(self.folder.cleanup)
        self.runtime = Path(self.folder.name)
        self.base = self.runtime / "hypr/test"
        self.base.mkdir(parents=True)
        for path in (self.runtime, self.runtime / "hypr", self.base):
            path.chmod(0o700)
        self.servers = []
        for name in (".socket.sock", ".socket2.sock"):
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.addCleanup(server.close)
            server.bind(str(self.base / name))
            server.listen(4)
            self.servers.append(server)
        (self.runtime / ".hyprveil-lab").write_text(json.dumps({"runtime_dir": str(self.runtime), "signature": "test", "pid": os.getpid()}))
        (self.runtime / ".hyprveil-lab").chmod(0o600)

    def tearDown(self):
        for server in self.servers:
            server.close()
        self.folder.cleanup()

    def admitted(self):
        return watch.BoundSession(self.runtime, "test", lab=True)

    @mock.patch.object(watch, "process_identity", return_value=(os.getpid(), b"original-start"))
    def test_socket_inode_replacement_is_not_rebound(self, identity):
        session = self.admitted()
        try:
            session.verify()
            path = self.base / ".socket.sock"
            path.unlink()
            replacement = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.servers.append(replacement)
            replacement.bind(str(path))
            replacement.listen(1)
            with self.assertRaises(watch.Refused):
                session.verify()
        finally:
            session.close()

    @mock.patch.object(watch, "process_identity", side_effect=[(os.getpid(), b"original-start"), (os.getpid(), b"original-start"), (os.getpid(), b"new-start")])
    def test_pid_reuse_is_not_accepted(self, identity):
        session = self.admitted()
        try:
            with self.assertRaises(watch.Refused):
                session.verify()
        finally:
            session.close()

    def test_nonstandard_runtime_requires_explicit_marked_lab(self):
        with self.assertRaises(watch.Refused):
            watch.BoundSession(self.runtime, "test")
        self.runtime.chmod(0o755)
        with self.assertRaises(watch.Refused):
            self.admitted()

    @mock.patch.object(watch, "process_identity", return_value=(os.getpid(), b"original-start"))
    def test_symlink_socket_and_mismatched_lab_marker_refused(self, identity):
        path = self.base / ".socket2.sock"
        path.rename(self.base / "other.sock")
        path.symlink_to(self.base / "other.sock")
        with self.assertRaises(watch.Refused):
            self.admitted()
        path.unlink()
        (self.base / "other.sock").rename(path)
        (self.runtime / ".hyprveil-lab").write_text(json.dumps({"runtime_dir": str(self.runtime), "signature": "other", "pid": os.getpid()}))
        with self.assertRaises(watch.Refused):
            self.admitted()


class QueryTests(unittest.TestCase):
    def launched(self, source):
        original = subprocess.Popen
        seen = []
        def child(argv, **kwargs):
            seen.append((argv, kwargs))
            return original([sys.executable, "-c", source], **kwargs)
        return mock.patch.object(watch.subprocess, "Popen", side_effect=child), seen

    def test_fixed_command_uses_validated_atomic_response(self):
        patch, seen = self.launched("print(" + repr(json.dumps(state())) + ")")
        with patch:
            self.assertEqual(watch.query(Path("/tmp/lab"), "abc"), state())
        self.assertEqual(seen[0][0], ["/usr/bin/hyprctl", "-i", "abc", "hyprveil", "active-privacy"])
        self.assertEqual(seen[0][1]["stderr"], subprocess.DEVNULL)
        self.assertNotIn("shell", seen[0][1])

    def test_oversized_stdout_is_killed_before_it_can_accumulate(self):
        patch, _ = self.launched("import sys; sys.stdout.write('x'*1000000); sys.stdout.flush()")
        with patch, self.assertRaises(watch.Refused):
            watch.query(Path("/tmp/lab"), "abc")

    def test_timed_out_child_is_killed_and_reaped(self):
        patch, _ = self.launched("import time; time.sleep(10)")
        started = time.monotonic()
        with patch, self.assertRaises(watch.Refused):
            watch.query(Path("/tmp/lab"), "abc")
        self.assertLess(time.monotonic() - started, 2.0)


if __name__ == "__main__":
    unittest.main()
