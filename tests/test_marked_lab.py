"""The optional stock-panel fixture admits only explicitly isolated labs."""
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
import marked_lab


class MarkedLabTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="hv-")
        self.addCleanup(self.folder.cleanup)
        self.runtime = Path(self.folder.name)
        self.runtime.chmod(0o700)
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(self.server.close)
        self.server.bind(str(self.runtime / "wayland-1"))
        self.marker = self.runtime / ".hyprveil-lab"
        self.data = {"runtime_dir": str(self.runtime), "signature": "synthetic-123", "pid": 123,
                     "wayland_display": "wayland-1", "parent_signature": "parent-456"}
        self.marker.write_text(json.dumps(self.data))
        self.marker.chmod(0o600)
        self.environment = {b"XDG_RUNTIME_DIR": str(self.runtime).encode(), b"HYPRVEIL_LAB_RUNTIME": str(self.runtime).encode(),
                            b"LIBSEAT_BACKEND": b"hyprveil-disabled"}
        self.session = Mock(target=(123, b"stable-start"))

    def load(self):
        with patch.object(marked_lab.watch, "BoundSession", return_value=self.session), patch.object(marked_lab, "proc_env", return_value=self.environment):
            return marked_lab.load_lab(self.runtime)

    def test_owned_marked_isolated_session_is_verified_and_closed(self):
        runtime, data = self.load()
        self.assertEqual(runtime, self.runtime)
        self.assertEqual(data, self.data)
        self.session.verify.assert_called_once_with()
        self.session.close.assert_called_once_with()

    def test_lab_environment_is_fixed_and_cannot_inherit_desktop_services(self):
        with patch.dict(os.environ, {"LD_PRELOAD": "bad", "DISPLAY": ":0", "DBUS_SESSION_BUS_ADDRESS": "secret", "PATH": "/tmp"}):
            value = marked_lab.lab_env(self.runtime, self.data)
        self.assertEqual(value["PATH"], "/usr/bin:/bin")
        self.assertEqual(value["WAYLAND_DISPLAY"], "wayland-1")
        for key in ("LD_PRELOAD", "DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "WAYLAND_SOCKET"):
            self.assertNotIn(key, value)

    def test_desktop_runtime_is_refused_without_socket_access(self):
        with self.assertRaises((OSError, marked_lab.watch.Refused)):
            marked_lab.load_lab(Path(f"/run/user/{os.getuid()}"))

    def test_unsafe_or_duplicate_marker_is_refused(self):
        good = self.marker.read_bytes()
        other = self.runtime / "other-marker"
        other.write_bytes(good)
        other.chmod(0o600)
        for kind in ("symlink", "hardlink", "writable", "oversized", "duplicate"):
            with self.subTest(kind=kind):
                self.marker.unlink()
                if kind == "symlink":
                    self.marker.symlink_to(other)
                elif kind == "hardlink":
                    os.link(other, self.marker)
                else:
                    self.marker.write_bytes(b"x" * 4097 if kind == "oversized" else b'{"pid":123,"pid":123}' if kind == "duplicate" else good)
                    self.marker.chmod(0o666 if kind == "writable" else 0o600)
                with self.assertRaises((OSError, marked_lab.watch.Refused)):
                    self.load()

    def test_physical_or_wrong_runtime_process_is_refused(self):
        for key in (b"XDG_RUNTIME_DIR", b"HYPRVEIL_LAB_RUNTIME", b"LIBSEAT_BACKEND"):
            with self.subTest(key=key):
                original = self.environment[key]
                self.environment[key] = b"wrong"
                with self.assertRaises(marked_lab.watch.Refused):
                    self.load()
                self.environment[key] = original

    def test_marker_peer_disagreement_is_refused_and_session_closed(self):
        self.session.target = (124, b"stable-start")
        with self.assertRaises(marked_lab.watch.Refused):
            self.load()
        self.session.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
