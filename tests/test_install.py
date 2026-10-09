"""Standalone GUI installation uses temporary HOME and never starts Hyprland."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import files

spec = importlib.util.spec_from_file_location("gui_install", ROOT / "tools/install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="hyprveil-gui-install-")
        self.addCleanup(self.folder.cleanup)
        self.home = Path(self.folder.name)
        self.plugins = self.home / ".config/omarchy/plugins"
        self.plugins.mkdir(parents=True)
        self.shell = self.plugins.parent / "shell.json"
        self.initial = {"bar": {"layout": {"left": [{"id": "omarchy.menu"}], "center": [], "right": [{"id": "omarchy.clock"}]}}, "custom": "retain"}
        self.shell.write_bytes(files.encoded(self.initial))
        self.shell.chmod(0o600)
        self.cli = self.home / ".local/bin/hyprveil"
        self.cli.parent.mkdir(parents=True)
        self.cli.write_text("#!/usr/bin/python3\nraise SystemExit('installation must not execute me')\n")
        self.cli.chmod(0o755)
        self.target = self.plugins / "io.github.objlako.hyprveil"
        self.home_patch = patch.object(Path, "home", return_value=self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)
        # Reports are kept inside the fixture rather than the checkout.
        # Use the actual source path for source admission; artifacts location
        # is redirected through ensure/temporary-directory helpers below.
        self.artifacts = self.home / "artifacts"
        self.artifacts.mkdir()
        original = installer.tempfile.mkdtemp
        self.temp_patch = patch.object(installer.tempfile, "mkdtemp", side_effect=lambda **kwargs: original(prefix=kwargs.get("prefix", "tmp"), dir=self.artifacts))
        self.temp_patch.start()
        self.addCleanup(self.temp_patch.stop)

    def run_install(self, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return installer.main(list(args))

    def test_fresh_install_is_standalone_preserves_layout_and_manifest_is_last(self):
        written = []
        original = files.atomic
        def record(path, contents, mode):
            if path.is_relative_to(self.target):
                written.append(str(path.relative_to(self.target)))
            return original(path, contents, mode)
        with patch.object(files, "atomic", side_effect=record):
            report = self.run_install()
        self.assertTrue(report["installed"])
        self.assertEqual(report["controller"], str(self.target / "panel-controller"))
        self.assertEqual(written[-1], "manifest.json")
        self.assertEqual(len(written), len(installer.RUNTIME_FILES))
        self.assertEqual(stat.S_IMODE((self.target / "privacy-watch").stat().st_mode), 0o755)
        self.assertEqual(stat.S_IMODE((self.target / "Panel.qml").stat().st_mode), 0o644)
        current = json.loads(self.shell.read_bytes())
        self.assertEqual(current["custom"], "retain")
        self.assertEqual(current["bar"]["layout"]["left"], self.initial["bar"]["layout"]["left"])
        self.assertEqual([row["id"] for row in current["bar"]["layout"]["right"]], ["io.github.objlako.hyprveil", "omarchy.clock"])
        self.assertEqual(Path(report["backup"]).read_bytes(), files.encoded(self.initial))
        self.assertEqual(stat.S_IMODE(Path(report["backup"]).stat().st_mode), 0o600)

    def test_repeat_install_never_duplicates_bar_entry(self):
        self.run_install()
        self.run_install()
        layout = json.loads(self.shell.read_bytes())["bar"]["layout"]
        self.assertEqual(sum(row.get("id") == "io.github.objlako.hyprveil" for rows in layout.values() for row in rows), 1)

    def test_old_flat_install_requires_explicit_migration_and_retains_files(self):
        legacy = self.plugins / "sky.hyprveil"
        legacy.mkdir()
        legacy_files = {"Panel.qml": b"// retained 1.4.0 custom panel\n", "manifest.json": b'{"id":"sky.hyprveil","version":"1.4.0"}\n',
                        "privacy-watch": b"# retained legacy helper\n"}
        for name, contents in legacy_files.items():
            (legacy / name).write_bytes(contents)
        self.initial["bar"]["layout"]["left"].append({"id": "sky.hyprveil", "settings": {"retain": True}})
        self.initial["bar"]["layout"]["right"].insert(0, {"id": "sky.screen-privacy"})
        self.shell.write_bytes(files.encoded(self.initial))
        before = self.shell.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "--update"):
            self.run_install()
        self.assertFalse(self.target.exists())
        self.assertEqual(self.shell.read_bytes(), before)
        report = self.run_install("--update")
        layout = json.loads(self.shell.read_bytes())["bar"]["layout"]
        self.assertEqual(layout["left"][-1], {"id": installer.PLUGIN_ID, "settings": {"retain": True}})
        entries = [item for values in layout.values() for item in values]
        self.assertEqual(sum(item.get("id") == installer.PLUGIN_ID for item in entries), 1)
        self.assertFalse(any(item.get("id") in installer.LEGACY_IDS for item in entries))
        self.assertEqual(Path(report["backup"]).read_bytes(), before)
        for name, contents in legacy_files.items():
            self.assertEqual((legacy / name).read_bytes(), contents)
            backup = Path(report["backup"]).parent / "legacy-sky.hyprveil" / name
            self.assertEqual(backup.read_bytes(), contents)
            self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)
        self.assertEqual(json.loads((self.target / "manifest.json").read_text())["version"], "1.6.2")

    def test_existing_new_entry_wins_and_duplicate_owned_eyes_are_removed(self):
        self.initial["bar"]["layout"]["left"].append({"id": "sky.hyprveil"})
        self.initial["bar"]["layout"]["right"] = [{"id": installer.PLUGIN_ID, "settings": {"keep": 42}},
            {"id": installer.PLUGIN_ID}, {"id": "sky.screen-privacy"}, {"id": "another.privacy"}]
        self.shell.write_bytes(files.encoded(self.initial))
        self.run_install("--update")
        layout = json.loads(self.shell.read_bytes())["bar"]["layout"]
        self.assertEqual(layout["right"], [{"id": installer.PLUGIN_ID, "settings": {"keep": 42}}, {"id": "another.privacy"}])
        self.assertEqual(layout["left"], [{"id": "omarchy.menu"}])

    def test_string_form_legacy_ids_are_migrated_without_touching_unrelated_strings(self):
        self.initial["bar"]["layout"]["right"] = ["sky.hyprveil", "sky.screen-privacy", "other.privacy"]
        self.shell.write_bytes(files.encoded(self.initial))
        with self.assertRaisesRegex(RuntimeError, "--update"):
            self.run_install()
        self.run_install("--update")
        self.assertEqual(json.loads(self.shell.read_bytes())["bar"]["layout"]["right"], [{"id": installer.PLUGIN_ID}, "other.privacy"])

    def test_git_managed_marketplace_install_is_refused_before_file_or_layout_writes(self):
        self.target.mkdir()
        (self.target / ".git").mkdir()
        panel = self.target / "Panel.qml"
        panel.write_text("// local Git checkout edit\n")
        before = self.shell.read_bytes()
        for args in ((), ("--update",)):
            with self.assertRaisesRegex(RuntimeError, "omarchy plugin update"):
                self.run_install(*args)
            self.assertEqual(panel.read_text(), "// local Git checkout edit\n")
            self.assertEqual(self.shell.read_bytes(), before)
            self.assertFalse((self.target / "manifest.json").exists())

    def test_unsafe_preset_directory_is_refused_before_any_widget_write(self):
        outside = self.home / "outside"
        outside.mkdir()
        self.target.mkdir()
        for kind in ("symlink", "writable"):
            assets = self.target / "assets"
            if kind == "symlink":
                assets.symlink_to(outside, target_is_directory=True)
            else:
                assets.mkdir(mode=0o777)
                assets.chmod(0o777)
            before = self.shell.read_bytes()
            with self.assertRaises((OSError, files.Refused)):
                self.run_install("--update")
            self.assertEqual(self.shell.read_bytes(), before)
            self.assertFalse((self.target / "Panel.qml").exists())
            self.assertFalse((outside / "presets").exists())
            if kind == "symlink":
                assets.unlink()
            else:
                assets.rmdir()

    def test_unsafe_legacy_file_is_refused_before_new_install(self):
        legacy = self.plugins / "sky.hyprveil"
        legacy.mkdir()
        (legacy / "Panel.qml").symlink_to(self.cli)
        with self.assertRaises((OSError, files.Refused)):
            self.run_install("--update")
        self.assertFalse(self.target.exists())
        self.assertEqual(self.shell.read_bytes(), files.encoded(self.initial))

    def test_first_user_plugin_install_creates_plugins_directory(self):
        self.plugins.rmdir()
        report = self.run_install()
        self.assertTrue(report["installed"])
        self.assertTrue(self.target.is_dir())

    def test_legacy_eye_is_replaced_without_removing_helpers(self):
        self.initial["bar"]["layout"]["right"].insert(0, {"id": "sky.screen-privacy"})
        self.shell.write_bytes(files.encoded(self.initial))
        legacy = self.plugins / "sky.screen-privacy"
        legacy.mkdir()
        helper = legacy / "privacy-status"
        helper.write_text("legacy helper retained for existing bindings\n")
        self.run_install("--update")
        layout = json.loads(self.shell.read_bytes())["bar"]["layout"]
        self.assertEqual([row["id"] for row in layout["right"]], ["io.github.objlako.hyprveil", "omarchy.clock"])
        self.assertEqual(helper.read_text(), "legacy helper retained for existing bindings\n")

    def test_legacy_eye_is_removed_when_new_widget_already_exists(self):
        self.initial["bar"]["layout"]["right"] = [{"id": "io.github.objlako.hyprveil"}, {"id": "sky.screen-privacy"}, {"id": "omarchy.clock"}]
        self.shell.write_bytes(files.encoded(self.initial))
        self.run_install("--update")
        self.assertEqual([row["id"] for row in json.loads(self.shell.read_bytes())["bar"]["layout"]["right"]], ["io.github.objlako.hyprveil", "omarchy.clock"])

    def test_owned_customization_requires_update_and_is_backed_up(self):
        self.run_install()
        edited = b"// deliberate local customization\n"
        (self.target / "Eye.qml").write_bytes(edited)
        with self.assertRaisesRegex(RuntimeError, "--update"):
            self.run_install()
        self.assertEqual((self.target / "Eye.qml").read_bytes(), edited)
        report = self.run_install("--update")
        backup = Path(report["backup"]).parent / "Eye.qml"
        self.assertEqual(backup.read_bytes(), edited)
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)

    def test_dependency_uses_known_owned_controller_symlink(self):
        self.cli.unlink()
        controller = self.home / ".local/share/hyprveil/controller.py"
        controller.parent.mkdir(parents=True)
        controller.write_text("#!/usr/bin/python3\n")
        controller.chmod(0o755)
        self.cli.symlink_to(controller)
        self.assertEqual(files.controller_path(self.home), self.cli)
        self.assertTrue(self.run_install()["installed"])

    def test_receipt_free_install_does_not_require_or_execute_a_legacy_cli(self):
        for kind in ("missing", "unrelated", "non-executable", "writable"):
            with self.subTest(kind=kind):
                self.cli.unlink(missing_ok=True)
                if kind == "unrelated":
                    self.cli.symlink_to("/usr/bin/python3")
                elif kind != "missing":
                    self.cli.write_text("#!/usr/bin/python3\n")
                    self.cli.chmod(0o644 if kind == "non-executable" else 0o777)
                report = self.run_install()
                self.assertTrue(report["installed"])
                self.assertTrue((self.target / "native_cli.py").is_file())
                self.assertTrue((self.target / "native_service.py").is_file())
                self.assertEqual(report["controller"], str(self.target / "panel-controller"))

    def test_links_fifo_and_group_writable_plugin_file_are_refused(self):
        self.run_install()
        item = self.target / "Eye.qml"
        outside = self.home / "outside"
        outside.write_bytes(item.read_bytes())
        for kind in ("symlink", "broken-symlink", "hardlink", "fifo", "writable"):
            with self.subTest(kind=kind):
                item.unlink()
                if kind == "symlink":
                    item.symlink_to(outside)
                elif kind == "broken-symlink":
                    item.symlink_to(self.home / "nonexistent")
                elif kind == "hardlink":
                    os.link(outside, item)
                elif kind == "fifo":
                    os.mkfifo(item, 0o600)
                else:
                    item.write_bytes(outside.read_bytes())
                    item.chmod(0o666)
                with self.assertRaises((OSError, files.Refused)):
                    self.run_install("--update")

    def test_unrecognized_layout_refused_before_plugin_write(self):
        self.shell.write_text('{"bar":{"layout":{"right":"invalid"}}}')
        with self.assertRaisesRegex(RuntimeError, "layout"):
            self.run_install()
        self.assertFalse(self.target.exists())

    def test_shell_edit_during_install_is_preserved(self):
        original = files.atomic
        edited = files.encoded({"bar": {"layout": {"right": []}}, "new": "user edit"})
        def concurrent(path, contents, mode):
            result = original(path, contents, mode)
            if path == self.target / "manifest.json":
                self.shell.write_bytes(edited)
            return result
        with patch.object(files, "atomic", side_effect=concurrent), self.assertRaisesRegex(RuntimeError, "changed"):
            self.run_install()
        self.assertEqual(self.shell.read_bytes(), edited)


if __name__ == "__main__":
    unittest.main()
