"""Receipt-free panel transport and narrowly retained legacy loading."""
import contextlib
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
loader = importlib.machinery.SourceFileLoader("panel_controller", str(ROOT / "panel-controller"))
spec = importlib.util.spec_from_loader(loader.name, loader)
controller = importlib.util.module_from_spec(spec)
loader.exec_module(controller)


class Executed(Exception):
    pass


class PanelControllerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="hyprveil-panel-controller-")
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        home = patch.object(controller.Path, "home", return_value=self.home)
        home.start()
        self.addCleanup(home.stop)
        self.output = io.StringIO()
        self.error = io.StringIO()

    def receipt(self):
        folder = self.home / ".config/hyprveil"
        folder.mkdir(parents=True, mode=0o700)
        receipt = folder / "config.json"
        receipt.write_text(json.dumps({"version": 1, "enabled": True, "plugin": str(self.home / "release.so"),
            "plugin_sha256": "a" * 64, "compositor_sha256": "b" * 64, "abi_hash": controller.service.TESTED_ABI}))
        receipt.chmod(0o600)
        cli = self.home / ".local/bin/hyprveil"
        cli.parent.mkdir(parents=True)
        cli.write_text("#!/usr/bin/python3\nraise RuntimeError('must not execute during status')\n")
        cli.chmod(0o755)
        return receipt, cli

    def invoke(self, args):
        with contextlib.redirect_stdout(self.output), contextlib.redirect_stderr(self.error):
            return controller.main(args)

    def status(self, loaded=False):
        return {"loaded": loaded, "enabled": loaded, "load_supported": False, "persistence_supported": False,
                "desired_mode": "black", "appearance": dict(controller.service.DEFAULT_APPEARANCE), "status": None}

    def test_fresh_hyprpm_status_needs_no_legacy_cli_or_receipt(self):
        with patch.object(controller.native_cli, "Controller") as native, patch.object(controller.os, "execve") as execute:
            native.return_value.run.return_value = self.status()
            self.assertEqual(self.invoke(["status"]), 0)
            native.return_value.run.assert_called_once_with("status")
            execute.assert_not_called()
        self.assertFalse(json.loads(self.output.getvalue())["load_supported"])
        self.assertFalse((self.home / ".config").exists())

    def test_loaded_native_core_ignores_stale_legacy_receipt(self):
        receipt, _ = self.receipt()
        receipt.write_text("invalid leftover legacy settings")
        with patch.object(controller.native_cli, "Controller") as native:
            native.return_value.run.return_value = self.status(True)
            self.assertEqual(self.invoke(["status"]), 0)
        self.assertTrue(json.loads(self.output.getvalue())["loaded"])
        self.assertFalse(json.loads(self.output.getvalue())["load_supported"])

    def test_invalid_legacy_receipt_does_not_obscure_unloaded_hyprpm_state(self):
        receipt, _ = self.receipt()
        receipt.write_text("invalid leftover receipt")
        with patch.object(controller.native_cli, "Controller") as native:
            native.return_value.run.return_value = self.status()
            self.assertEqual(self.invoke(["status"]), 0)
        status = json.loads(self.output.getvalue())
        self.assertFalse(status["loaded"])
        self.assertFalse(status["load_supported"])

    def test_unloaded_legacy_install_retains_explicit_loading(self):
        _, cli = self.receipt()
        with patch.object(controller.native_cli, "Controller") as native, patch.object(controller.os, "execve") as execute:
            native.return_value.run.return_value = self.status()
            self.assertEqual(self.invoke(["status"]), 0)
            execute.assert_not_called()
        self.assertTrue(json.loads(self.output.getvalue())["load_supported"])
        for action in ("start", "enable"):
            with patch.object(controller.os, "execve", side_effect=Executed) as execute, self.assertRaises(Executed):
                self.invoke([action])
            self.assertEqual(execute.call_args.args[:2], (str(cli), [str(cli), action]))

    def test_hyprpm_load_is_delegated_to_hyprpm_not_native_controller(self):
        for action in ("start", "enable"):
            with patch.object(controller.os, "execve") as execute, patch.object(controller.native_cli, "main") as native:
                self.assertEqual(self.invoke([action]), 1)
                execute.assert_not_called()
                native.assert_not_called()
        self.assertIn("hyprpm enable hyprveil", self.error.getvalue())

    def test_unsafe_legacy_cli_cannot_gain_loading_support(self):
        receipt, cli = self.receipt()
        outside = self.home / "other.py"
        outside.write_text("raise RuntimeError('unrelated')")
        for kind in ("writable", "symlink", "hardlink", "fifo"):
            cli.unlink()
            if kind == "writable":
                cli.write_text("#!/bin/sh\n")
                cli.chmod(0o777)
            elif kind == "symlink":
                cli.symlink_to(outside)
            elif kind == "hardlink":
                os.link(outside, cli)
            else:
                os.mkfifo(cli, 0o600)
            with patch.object(controller.os, "execve") as execute:
                self.assertEqual(self.invoke(["start"]), 1)
                execute.assert_not_called()

    def test_regular_native_actions_use_bundle_even_with_stale_legacy_settings(self):
        receipt, _ = self.receipt()
        receipt.write_text("stale receipt")
        for args in (["spoiler"], ["configure", "--grain", "34"], ["reload-config"]):
            with patch.object(controller.native_cli, "main", return_value=0) as native, patch.object(controller.os, "execve") as execute:
                self.assertEqual(self.invoke(args), 0)
                native.assert_called_once_with(args)
                execute.assert_not_called()

    def test_bundled_parser_accepts_every_panel_preset_and_icon(self):
        for variant in ("prism", "signal", "aurora", "contour", "radar", "matte", "error404", "matrix", "anonymous", "glass"):
            for icon in ("eye", "lock", "shield", "none"):
                argv = ["configure", "--variant", variant, "--color", "#adcfc8", "--grain", "34",
                        "--speed", "125", "--darkness", "28", "--eye", "off" if icon == "none" else "on",
                        "--eye-size", "96", "--icon", icon, "--icon-opacity", "42"]
                with patch.object(controller.native_cli, "Controller") as native:
                    native.return_value.run.return_value = {"persisted": False}
                    self.assertEqual(self.invoke(argv), 0)
                    args = native.return_value.run.call_args.args
                    self.assertEqual(args[0], "configure")
                    self.assertEqual(args[2]["variant"], variant)
                    self.assertEqual(args[2]["icon"], icon)
                    self.assertEqual(args[2]["icon_opacity"], 42)
                    self.assertEqual(args[2]["eye"], icon != "none")

    def test_bundled_source_has_reviewable_content_hashes(self):
        provenance = json.loads((ROOT / "native-cli-provenance.json").read_text())
        for name, entry in provenance["files"].items():
            contents = (ROOT / name).read_bytes()
            self.assertEqual(hashlib.sha256(contents).hexdigest(), entry["bundled_sha256"])
            if name == "native_cli.py":
                contents = contents.replace(b"import native_service as service\n", b"import service\n")
            self.assertEqual(hashlib.sha256(contents).hexdigest(), entry["source_sha256"])


if __name__ == "__main__":
    unittest.main()
