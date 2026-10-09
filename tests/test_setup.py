"""Independent setup failure tests: real private files, fake manager transport.

No test invokes Hyprpm, sudo, a real compositor or the desktop shell.
"""
import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import pwd
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("reviewed_setup", ROOT / "tools/setup.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)
REAL_COMMAND = setup.command


class SetupFailureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="hyprveil-setup-review-")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.instance = setup.Setup(self.home, self.home / "manager-cache")
        self.instance.hypr.mkdir(parents=True)
        self.original = b"-- unrelated user configuration\nhl.config({general={border_size=2}})\n"
        self.instance.main.write_bytes(self.original)
        self.instance.main.chmod(0o600)
        self.instance.cache.mkdir()
        (self.instance.cache / "state.toml").write_text("[state]\nhash = '" + setup.service.TESTED_ABI + "'\n")
        header = self.instance.cache / "headersRoot/share/pkgconfig/hyprland.pc"
        header.parent.mkdir(parents=True)
        header.write_text("Name: Hyprland\nVersion: 0.56.2\n")
        version_header = self.instance.cache / "headersRoot/include/hyprland/src/version.h"
        version_header.parent.mkdir(parents=True)
        version_header.write_text('#define GIT_COMMIT_HASH "' + setup.service.TESTED_ABI.split('_', 1)[0] + '"\n')
        self.core = self.home / "reviewed core"
        self.core.mkdir()
        # Actual published release manifest includes an ancestor commit pin.
        # Explicit add revision must remain nonempty so Hyprpm uses HEAD.
        (self.core / "hyprpm.toml").write_bytes((ROOT / "tests/fixtures/hyprpm-release.toml").read_bytes())
        self.pin = {"repository": setup.REPOSITORY, "revision": "a" * 40, "version": "0.5.0"}
        self.args = argparse.Namespace(yes=True, plugin_only=False, hyprpm_update=False, core_source=self.core)
        self.calls = []
        self.command_options = []
        self.loaded = False
        self.fail = None
        self.on_command = None
        self.reload_error = False
        self.dirty = ""
        self.native_version = "0.5.0"
        self.admit_load = True
        self.output = io.StringIO()
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.dict(os.environ, HYPRLAND_INSTANCE_SIGNATURE="fixture-only"))
        stack.enter_context(patch.object(setup, "release", return_value=self.pin))
        stack.enter_context(patch.object(setup, "command", side_effect=self.command))
        stack.enter_context(patch.object(setup, "ask", return_value=False))
        stack.enter_context(patch.object(setup.shutil, "which", return_value="/usr/bin/pacman"))
        controller = stack.enter_context(patch.object(setup.native_cli, "Controller"))
        controller.return_value.run.side_effect = self.controller
        controller.return_value.plugins.side_effect = lambda: [{"name": "hyprveil", "version": self.native_version}]
        stack.enter_context(contextlib.redirect_stdout(self.output))
        stack.enter_context(contextlib.redirect_stderr(self.output))

    def controller(self, action):
        self.calls.append(("controller", action))
        return {"loaded": self.loaded}

    def command(self, argv, **kwargs):
        argv = tuple(map(str, argv))
        self.calls.append(argv)
        self.command_options.append((argv, dict(kwargs)))
        if self.on_command:
            self.on_command(argv)
        if self.fail and argv[:len(self.fail)] == self.fail:
            raise subprocess.CalledProcessError(1, argv)
        if argv == ("hyprctl", "version", "-j"):
            return json.dumps({"abiHash": setup.service.TESTED_ABI, "commit": "running"})
        if argv == ("hyprctl", "configerrors"):
            return "injected invalid configuration" if self.reload_error and ("hyprctl", "reload") in self.calls else ""
        if argv[:1] == ("git",):
            if "rev-parse" in argv:
                return self.pin["revision"] + "\n"
            if "status" in argv:
                return self.dirty
            return ""
        if argv[:2] == ("hyprpm", "add"):
            # Pinned main.cpp calls updateHeaders(false) itself after its
            # full ABI hash gate, repairing a missing pc without global sync.
            header = self.instance.cache / "headersRoot/share/pkgconfig/hyprland.pc"
            header.write_text("Name: Hyprland\nVersion: 0.56.2\n")
            folder = self.instance.cache / "hyprveil"
            folder.mkdir(exist_ok=True)
            (folder / "state.toml").write_text("[repository]\nname = 'hyprveil'\nurl = " + repr(argv[2]) + "\nrev = '" + argv[3] + "'\n[hyprveil]\nfilename = 'hyprveil.so'\nenabled = false\nfailed = false\n")
            (folder / "hyprveil.so").write_bytes(b"synthetic manager build; never executed")
        elif argv == ("hyprpm", "enable", "hyprveil"):
            path = self.instance.cache / "hyprveil/state.toml"
            path.write_text(path.read_text().replace("enabled = false", "enabled = true"))
        elif argv == ("hyprpm", "remove", "hyprveil"):
            shutil.rmtree(self.instance.cache / "hyprveil")
        elif argv == ("hyprpm", "update"):
            (self.instance.cache / "state.toml").write_text("[state]\nhash='" + setup.service.TESTED_ABI + "'\n")
        elif argv[:3] == ("hyprctl", "plugin", "load"):
            self.loaded = self.admit_load
        return ""

    def install(self):
        return self.instance.install(self.args)

    def manager_calls(self):
        return [call for call in self.calls if call[:1] == ("hyprpm",)]

    def assert_no_published_setup(self):
        self.assertEqual(self.instance.main.read_bytes(), self.original)
        for path in (self.instance.bootstrap, self.instance.settings, self.instance.receipt):
            self.assertFalse(path.exists(), path)

    def test_fresh_setup_persists_settings_and_selectively_loads_only_hyprveil(self):
        unrelated = self.instance.cache / "unrelated"
        unrelated.mkdir()
        foreign = unrelated / "state.toml"
        foreign.write_text("name='other-plugin'\n[other]\nenabled=true\n")
        previous = foreign.read_bytes()
        self.install()
        self.assertTrue(self.loaded)
        self.assertEqual(foreign.read_bytes(), previous)
        self.assertEqual(self.manager_calls(), [("hyprpm", "add", str(self.core), self.pin["revision"]),
                                              ("hyprpm", "enable", "hyprveil")])
        self.assertEqual(self.instance.main.read_bytes().count(setup.BEGIN.encode()), 1)
        self.assertIn(self.original.rstrip(), self.instance.main.read_bytes())
        values = setup.service.parse_lua_settings(self.instance.settings.read_bytes())[-1]
        self.assertEqual(values["mode"], "spoiler")
        self.assertEqual(values["icon"], "eye")
        record = json.loads(self.instance.receipt.read_bytes())
        self.assertEqual(record["native_source"], str(self.core))
        self.assertEqual(self.instance.receipt.stat().st_mode & 0o777, 0o600)
        self.assertIn(("controller", "reload-config"), self.calls)

    def test_no_terminal_consent_cannot_create_or_enable_a_setup(self):
        self.args.yes = False
        with self.assertRaises(setup.files.Refused):
            self.install()
        self.assert_no_published_setup()
        self.assertFalse(self.instance.dest.exists())
        self.assertFalse(self.manager_calls())

    def test_legacy_loader_refused_before_any_external_command_or_write(self):
        for name, contents in (("hyprveil.lua", "-- old loader"),
                               ("autostart.lua", "-- BEGIN HYPRVEIL MANAGED AUTOLOAD\n")):
            with self.subTest(name=name):
                path = self.instance.hypr / name
                path.write_text(contents)
                with self.assertRaises(setup.files.Refused):
                    self.install()
                path.unlink()
                self.assertFalse(self.calls)
                self.assert_no_published_setup()

    def test_global_header_update_requires_separate_explicit_scope(self):
        (self.instance.cache / "state.toml").write_text("[state]\nhash = 'old-headers'\n")
        with self.assertRaises(setup.files.Refused):
            self.install()
        self.assertFalse(self.manager_calls())
        self.assert_no_published_setup()
        self.args.hyprpm_update = True
        self.install()
        self.assertEqual(self.manager_calls()[0], ("hyprpm", "update"))
        self.assertEqual(self.manager_calls().count(("hyprpm", "update")), 1)
        options = [options for argv, options in self.command_options if argv == ("hyprpm", "update")]
        self.assertEqual(options, [{"compositor": False, "allowed": (0, 1)}])

    def test_empty_header_bootstrap_refuses_failed_or_changed_postconditions(self):
        pc = self.instance.cache / "headersRoot/share/pkgconfig/hyprland.pc"
        header = self.instance.cache / "headersRoot/include/hyprland/src/version.h"
        foreign = self.instance.cache / "other/state.toml"
        original_header = header.read_text()
        for corruption in ("global-abi", "pc-version", "source-hash", "new-repository"):
            with self.subTest(corruption=corruption):
                (self.instance.cache / "state.toml").write_text("[state]\nhash='stale'\n")
                pc.write_text("Name: Hyprland\nVersion: 0.56.2\n")
                header.write_text(original_header)
                foreign.unlink(missing_ok=True)
                def incomplete_update(argv, **kwargs):
                    value = self.command(argv, **kwargs)
                    if tuple(argv) == ("hyprpm", "update"):
                        if corruption == "global-abi":
                            (self.instance.cache / "state.toml").write_text("[state]\nhash='still-stale'\n")
                        elif corruption == "pc-version":
                            pc.write_text("Version: 0.56.1\n")
                        elif corruption == "source-hash":
                            header.write_text('#define GIT_COMMIT_HASH "' + "b" * 40 + '"\n')
                        else:
                            foreign.parent.mkdir(exist_ok=True)
                            foreign.write_text("[repository]\nname='other'\n[other]\nenabled=true\nfailed=false\n")
                    return value
                with patch.object(setup, "command", side_effect=incomplete_update), self.assertRaises(setup.files.Refused):
                    self.instance.update_headers()
                self.assert_no_published_setup()

    def test_nonempty_foreign_manager_store_never_masks_global_update_failure(self):
        foreign = self.instance.cache / "other/state.toml"
        foreign.parent.mkdir()
        foreign.write_text("[repository]\nname='other'\n[other]\nenabled=true\nfailed=false\n")
        # This foreign provider is intentionally excluded from repositories(),
        # but it must still choose the ordinary, consented manager path.
        self.assertEqual(self.instance.repositories(), [])
        self.instance.update_headers()
        options = [options for argv, options in self.command_options if argv == ("hyprpm", "update")]
        self.assertEqual(options, [{"compositor": True, "allowed": (0,)}])
        self.fail = ("hyprpm", "update")
        with self.assertRaises(subprocess.CalledProcessError):
            self.instance.update_headers()

    def test_build_enable_and_load_failures_do_not_publish_config_or_receipt(self):
        for failed in (("hyprpm", "add"), ("hyprpm", "enable"), ("hyprctl", "plugin", "load")):
            with self.subTest(command=failed):
                self.fail = failed
                with self.assertRaises(subprocess.CalledProcessError):
                    self.install()
                self.assert_no_published_setup()
                self.assertFalse(self.loaded)
                self.fail = None

    def test_rejected_config_rolls_back_private_files_and_original_mode(self):
        self.reload_error = True
        with self.assertRaises(setup.files.Refused):
            self.install()
        self.assert_no_published_setup()
        self.assertEqual(self.instance.main.stat().st_mode & 0o777, 0o600)
        self.assertFalse(self.loaded)
        self.assertEqual((self.instance.backup / ".config/hypr/hyprland.lua").read_bytes(), self.original)

    def test_ctrl_c_during_first_config_reload_rolls_back_and_allows_retry(self):
        fired = False
        def interrupt_once(argv):
            nonlocal fired
            if argv == ("hyprctl", "reload") and not fired:
                fired = True
                raise KeyboardInterrupt
        self.on_command = interrupt_once
        with self.assertRaises(KeyboardInterrupt):
            self.install()
        self.assertTrue(fired)
        self.assert_no_published_setup()
        self.assertEqual(self.instance.main.stat().st_mode & 0o777, 0o600)
        self.on_command = None
        self.install()
        self.assertTrue(self.loaded)
        self.assertFalse(self.instance.old_receipt()["pending_login"])

    def test_edit_during_native_build_is_not_overwritten_by_stale_main_snapshot(self):
        edited = self.original + b"-- user edit during long native build\n"
        def edit(argv):
            if argv[:2] == ("hyprpm", "add"):
                self.instance.main.write_bytes(edited)
        self.on_command = edit
        with self.assertRaisesRegex(setup.files.Refused, "changed"):
            self.install()
        self.assertEqual(self.instance.main.read_bytes(), edited)
        self.assertFalse(self.instance.receipt.exists())

    def test_user_edit_during_failed_activation_keeps_a_resolvable_loader(self):
        edited = None
        def edit(argv):
            nonlocal edited
            if argv[:3] == ("hyprctl", "plugin", "load"):
                edited = self.instance.main.read_bytes() + b"-- concurrent user edit after setup block\n"
                self.instance.main.write_bytes(edited)
        self.on_command = edit
        self.fail = ("hyprctl", "plugin", "load")
        with self.assertRaises(subprocess.CalledProcessError):
            self.install()
        self.assertEqual(self.instance.main.read_bytes(), edited)
        if setup.BEGIN.encode() in edited:
            self.assertTrue(self.instance.bootstrap.exists(), "retained main config must not dofile a removed bootstrap")
            self.assertTrue(self.instance.settings.exists(), "retained bootstrap must not dofile removed settings")
            self.assertTrue((self.instance.dest / "setup.py").exists(), "retained startup must resolve its helper")

    def test_dirty_core_refused_before_manager_mutation(self):
        self.dirty = " M src/main.cpp\n"
        with self.assertRaisesRegex(setup.files.Refused, "clean"):
            self.install()
        self.assertFalse(self.manager_calls())
        self.assert_no_published_setup()

    def test_edited_setup_block_refused_before_manager_mutation(self):
        self.instance.main.write_bytes(self.original + setup.BLOCK.replace("dofile", "-- user edit\ndofile").encode())
        before = self.instance.main.read_bytes()
        with self.assertRaises(setup.files.Refused):
            self.install()
        self.assertEqual(self.instance.main.read_bytes(), before)
        self.assertFalse(self.manager_calls())

    def test_uninstall_removes_widget_but_keeps_native_startup_source_and_settings(self):
        self.install()
        paths = [self.instance.main, self.instance.bootstrap, self.instance.settings, self.instance.receipt,
                 *(self.instance.dest / name for name in setup.HELPERS), self.core / "hyprpm.toml"]
        before = {path: path.read_bytes() for path in paths}
        self.calls.clear()
        self.instance.uninstall()
        self.assertEqual(self.calls, [("omarchy", "plugin", "remove", "io.github.objlako.hyprveil")])
        self.assertEqual({path: path.read_bytes() for path in paths}, before)
        self.assertTrue(self.loaded)

    def test_invalid_receipt_fields_fail_as_typed_refusals(self):
        self.instance.conf.mkdir()
        for malformed in ({"schema": 1, "files": {str(self.instance.bootstrap): None}},
                          {"schema": 1, "files": {}, "native_owned": True, "native_source": 123},
                          {"schema": 1, "files": {}, "block_sha256": ["bad"]}):
            with self.subTest(record=malformed):
                self.instance.receipt.write_text(json.dumps(malformed))
                with self.assertRaises(setup.files.Refused):
                    self.instance.old_receipt()

    def test_native_filename_cannot_select_a_different_cached_binary(self):
        self.install()
        self.loaded = False
        path = self.instance.cache / "hyprveil/state.toml"
        path.write_text(path.read_text().replace("filename = 'hyprveil.so'", "filename = '../other.so'"))
        self.calls.clear()
        with self.assertRaises(setup.files.Refused):
            self.instance.activate()
        self.assertFalse(any(call[:3] == ("hyprctl", "plugin", "load") for call in self.calls))

    def test_owned_unloaded_core_repairs_on_normal_first_click_path(self):
        self.install()
        self.loaded = False
        self.calls.clear()
        self.install()
        self.assertEqual(self.manager_calls(), [("hyprpm", "remove", "hyprveil"),
                          ("hyprpm", "add", str(self.core), self.pin["revision"]), ("hyprpm", "enable", "hyprveil")])
        self.assertTrue(self.loaded)

    def test_fresh_repair_and_recovery_enable_never_synchronize_the_compositor(self):
        self.install()
        self.loaded = False
        self.install()
        self.loaded = False
        fired = False
        def fail_new_add_once(argv):
            nonlocal fired
            if argv[:2] == ("hyprpm", "add") and not fired:
                fired = True
                raise subprocess.CalledProcessError(2, argv)
        self.on_command = fail_new_add_once
        with self.assertRaises(subprocess.CalledProcessError):
            self.install()
        enables = [options for argv, options in self.command_options if argv == ("hyprpm", "enable", "hyprveil")]
        self.assertEqual(len(enables), 3, "fresh setup, repair and recovery must all use the guarded enable path")
        self.assertTrue(all(options.get("compositor") is False for options in enables))
        self.assertTrue(all(options.get("allowed") == (0, 1) for options in enables))
        removals = [options for argv, options in self.command_options if argv[:2] == ("hyprpm", "remove")]
        self.assertTrue(removals)
        self.assertTrue(all(options.get("compositor") is False for options in removals))

    def test_external_core_is_never_removed_by_default_or_explicit_repair(self):
        self.command(("hyprpm", "add", str(self.core), self.pin["revision"]))
        self.calls.clear()
        self.install()
        self.assertFalse(any(call[:2] == ("hyprpm", "remove") for call in self.calls))
        self.loaded = False
        self.args.plugin_only = True
        self.calls.clear()
        with self.assertRaisesRegex(setup.files.Refused, "outside"):
            self.install()
        self.assertFalse(self.manager_calls())

    def test_repair_rechecks_loaded_state_after_preparing_source(self):
        self.install()
        self.loaded = False
        self.calls.clear()
        def suddenly_loaded(argv):
            if argv[:1] == ("git",):
                self.loaded = True
        self.on_command = suddenly_loaded
        with self.assertRaisesRegex(setup.files.Refused, "loaded during"):
            self.install()
        self.assertFalse(self.manager_calls())
        self.assertTrue(self.loaded)

    def test_repair_restores_old_registration_after_add_or_enable_failure(self):
        self.install()
        previous = self.instance.receipt.read_bytes()
        for fail_once in (("hyprpm", "add"), ("hyprpm", "enable")):
            with self.subTest(command=fail_once):
                self.loaded = False
                self.calls.clear()
                fired = False
                def fail(argv):
                    nonlocal fired
                    if not fired and argv[:2] == fail_once:
                        fired = True
                        raise subprocess.CalledProcessError(1, argv)
                self.on_command = fail
                with self.assertRaises(subprocess.CalledProcessError):
                    self.install()
                self.assertTrue(fired)
                self.assertEqual(self.instance.receipt.read_bytes(), previous)
                repositories = self.instance.repositories()
                self.assertEqual(repositories[0][1]["repository"]["url"], str(self.core))
                self.assertTrue(repositories[0][1]["hyprveil"]["enabled"])
                self.assertEqual(self.manager_calls()[-2:], [("hyprpm", "add", str(self.core), self.pin["revision"]),
                                                           ("hyprpm", "enable", "hyprveil")])
                self.on_command = None

    def test_ctrl_c_after_owned_removal_restores_registration_and_keeps_files(self):
        self.install()
        paths = [self.instance.main, self.instance.bootstrap, self.instance.settings, self.instance.receipt]
        before = {path: path.read_bytes() for path in paths}
        for phase in ("during_remove_after_effect", "after_remove", "during_remove_before_effect"):
            with self.subTest(phase=phase):
                self.loaded = False
                self.on_command = None
                self.command(("hyprpm", "add", str(self.core), self.pin["revision"]))
                self.command(("hyprpm", "enable", "hyprveil"))
                self.calls.clear()
                fired = False
                def interrupt_once(argv):
                    nonlocal fired
                    match = (argv[:2] == ("hyprpm", "add")) if phase == "after_remove" else (argv == ("hyprpm", "remove", "hyprveil"))
                    if match and not fired:
                        fired = True
                        if phase == "during_remove_after_effect":
                            # The manager completed deletion just before the
                            # parent received Ctrl-C: command never returned.
                            shutil.rmtree(self.instance.cache / "hyprveil")
                        raise KeyboardInterrupt
                self.on_command = interrupt_once
                with self.assertRaises(KeyboardInterrupt):
                    self.install()
                self.assertTrue(fired)
                self.assertEqual({path: path.read_bytes() for path in paths}, before)
                repositories = self.instance.repositories()
                self.assertEqual(repositories[0][1]["repository"]["url"], str(self.core))
                self.assertEqual(repositories[0][1]["repository"]["rev"], self.pin["revision"])
                self.assertTrue(repositories[0][1]["hyprveil"]["enabled"])
                self.on_command = None

    def test_old_loaded_core_is_refused_without_unload_or_manager_mutation(self):
        self.loaded = True
        self.native_version = "0.4.0"
        with self.assertRaisesRegex(setup.files.Refused, "cold-login"):
            self.install()
        self.assertFalse(self.manager_calls())
        self.assert_no_published_setup()
        self.assertTrue(self.loaded)

    def test_already_loaded_startup_path_still_applies_managed_settings(self):
        self.install()
        self.calls.clear()
        self.instance.activate()
        self.assertIn(("controller", "reload-config"), self.calls)
        self.assertFalse(any(call[:3] == ("hyprctl", "plugin", "load") for call in self.calls))

    def test_cache_identity_uses_os_uid_instead_of_inherited_user_name(self):
        with patch.dict(os.environ, USER="other-user", LOGNAME="other-user"):
            instance = setup.Setup(self.home)
        self.assertEqual(instance.cache, Path("/var/cache/hyprpm") / pwd.getpwuid(os.getuid()).pw_name)

    def test_symlinked_source_is_refused_before_git_execution(self):
        link = self.home / "linked-source"
        link.symlink_to(self.core, target_is_directory=True)
        self.calls.clear()
        with self.assertRaises(setup.files.Refused):
            self.instance.source(self.pin, link)
        self.assertFalse(self.calls)

    def test_dangling_default_source_symlink_is_never_replaced_by_fetch(self):
        self.instance.dest.mkdir(parents=True)
        target = self.instance.dest / ("native-" + self.pin["revision"])
        target.symlink_to(self.home / "absent-native-target", target_is_directory=True)
        self.calls.clear()
        with self.assertRaises(setup.files.Refused):
            self.instance.source(self.pin)
        self.assertTrue(target.is_symlink())
        self.assertFalse(self.calls, "source ownership must be checked before fetching")

    def test_successful_load_request_without_admission_keeps_pending_startup(self):
        self.admit_load = False
        with self.assertRaises(setup.PendingLogin):
            self.install()
        self.assertFalse(self.loaded)
        self.assertIn(setup.BLOCK.encode(), self.instance.main.read_bytes())
        self.assertTrue(self.instance.settings.exists())
        self.assertTrue(self.instance.bootstrap.exists())
        self.assertTrue((self.instance.dest / "setup.py").exists())
        record = self.instance.old_receipt()
        self.assertTrue(record["pending_login"])
        self.assertTrue(record["native_owned"])
        self.assertNotIn("Hyprveil ready", self.output.getvalue())
        # A later admitted retry can repair this exact owned registration.
        self.admit_load = True
        self.install()
        self.assertTrue(self.loaded)
        self.assertFalse(self.instance.old_receipt()["pending_login"])

    def test_bootstrap_shell_command_round_trips_a_legal_complex_home(self):
        unusual = self.home / "home space' apostrophe $(printf nope) `printf nope`"
        self.instance = setup.Setup(unusual, self.instance.cache)
        self.instance.hypr.mkdir(parents=True)
        self.instance.main.write_bytes(self.original)
        self.install()
        # Execute Lua only with all Hyprland/shell APIs stubbed. This checks
        # Lua decoding first, then POSIX shell tokenization; no command runs.
        script = ('hl={permission=function() end, on=function(_,f) f() end, '
                  'exec_cmd=function(s) io.write(s) end}; dofile=function() end;\n' +
                  self.instance.bootstrap.read_text())
        result = subprocess.run(["/usr/bin/lua", "-"], input=script, text=True,
                                capture_output=True, check=True, timeout=5)
        self.assertEqual(shlex.split(result.stdout), ["/usr/bin/python3", str(self.instance.dest / "setup.py"), "--load-only"])

    def test_matching_header_hash_without_pc_is_repaired_by_add_without_global_update(self):
        (self.instance.cache / "headersRoot/share/pkgconfig/hyprland.pc").unlink()
        self.install()
        self.assertFalse(any(call == ("hyprpm", "update") for call in self.calls))
        self.assertEqual(self.manager_calls()[0][:2], ("hyprpm", "add"))
        self.assertTrue((self.instance.cache / "headersRoot/share/pkgconfig/hyprland.pc").exists())

    def test_adopted_external_url_and_revision_are_preserved_without_ownership(self):
        self.command(("hyprpm", "add", "https://example.invalid/foreign-core", "stable"))
        self.loaded = True
        self.calls.clear()
        self.install()
        record = self.instance.old_receipt()
        self.assertEqual(record["native_source"], "https://example.invalid/foreign-core")
        self.assertEqual(record["native_revision"], "stable")
        self.assertFalse(record["native_owned"])
        self.assertFalse(any(call[:2] == ("hyprpm", "remove") for call in self.calls))

    def test_loaded_owned_core_does_not_claim_an_unbuilt_new_release_revision(self):
        self.install()
        old_revision = self.pin["revision"]
        self.pin["revision"] = "b" * 40
        self.calls.clear()
        self.install()
        record = self.instance.old_receipt()
        self.assertEqual(record["native_revision"], old_revision)
        self.assertTrue(record["native_owned"])
        self.assertFalse(any(call[:2] == ("hyprpm", "add") for call in self.calls))

    def test_malformed_compositor_version_is_a_typed_early_refusal(self):
        for shape in ([], None, 42, "wrong"):
            with self.subTest(shape=shape):
                def malformed(argv, **kwargs):
                    return json.dumps(shape) if tuple(argv) == ("hyprctl", "version", "-j") else self.command(argv, **kwargs)
                with patch.object(setup, "command", side_effect=malformed), self.assertRaises(setup.files.Refused):
                    self.install()
                self.assert_no_published_setup()

    def test_startup_helper_rejects_fifo_hardlink_and_overlapping_setup_locks(self):
        self.instance.conf.mkdir()
        lock = self.instance.conf / ".lock"
        with patch.object(setup, "Setup", return_value=self.instance), patch.object(self.instance, "activate") as activate:
            os.mkfifo(lock, 0o600)
            self.assertEqual(setup.main(["--load-only"]), 1)
            activate.assert_not_called()
            lock.unlink()
            lock.write_bytes(b"")
            lock.chmod(0o600)
            other = self.instance.conf / "other-link"
            os.link(lock, other)
            self.assertEqual(setup.main(["--load-only"]), 1)
            activate.assert_not_called()
            other.unlink()
            with lock.open("rb") as held:
                setup.fcntl.flock(held, setup.fcntl.LOCK_EX | setup.fcntl.LOCK_NB)
                self.assertEqual(setup.main(["--load-only"]), 1)
                activate.assert_not_called()


class HyprpmEnableSubprocessTests(unittest.TestCase):
    """Model the reviewed manager's persisted-enable then global-sync order.

    A real subprocess sees the real command runner's final environment. The
    fixture's reconciliation only writes a temporary proof file; it has no
    sockets, root cache, actual Hyprpm or desktop access.
    """
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="hyprveil-enable-subprocess-")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.instance = setup.Setup(self.home, self.home / "manager-cache")
        self.folder = self.instance.cache / "hyprveil"
        self.folder.mkdir(parents=True)
        self.state = self.folder / "state.toml"
        self.source, self.revision = "https://example.invalid/reviewed-core", "a" * 40
        self.initial = ("[repository]\nname='hyprveil'\nurl='" + self.source + "'\nrev='" + self.revision +
                        "'\n[hyprveil]\nfilename='hyprveil.so'\nenabled=false\nfailed=false\n")
        self.state.write_text(self.initial)
        (self.folder / "hyprveil.so").write_bytes(b"fixture cache artifact; never executed")
        self.proof = self.home / "unrelated-fx-was-unloaded"
        self.fixture = self.home / "manager_fixture.py"
        self.fixture.write_text('''import os,sys
from pathlib import Path
home=Path(os.environ["HOME"])
state=home/"manager-cache/hyprveil/state.toml"
mode=sys.argv[1]
if mode=="enable-failed": sys.exit(1)
text=state.read_text().replace("enabled=false","enabled=true")
if mode=="failed-build": text=text.replace("failed=false","failed=true")
if mode=="wrong-revision": text=text.replace("rev='"+"a"*40+"'", "rev='"+"b"*40+"'")
state.write_text(text)
# Pinned main.cpp persists the flag BEFORE ensurePluginsLoadState(). The
# latter checks getenv(HIS), then reconciles all loaded modules against cache.
if "HYPRLAND_INSTANCE_SIGNATURE" in os.environ:
    (home/"unrelated-fx-was-unloaded").write_text("omarchy-fx")
    sys.exit(0)
print("PluginManager: no $HOME or $HYPRLAND_INSTANCE_SIGNATURE",file=sys.stderr)
sys.exit(1)
''')
        stack = contextlib.ExitStack(); self.addCleanup(stack.close)
        stack.enter_context(patch.dict(os.environ, HOME=str(self.home), HYPRLAND_INSTANCE_SIGNATURE="fixture-compositor"))
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        stack.enter_context(contextlib.redirect_stderr(io.StringIO()))

    def transport(self, mode):
        def run(argv, **kwargs):
            self.assertEqual(tuple(argv), ("hyprpm", "enable", "hyprveil"))
            return REAL_COMMAND([sys.executable, self.fixture, mode], **kwargs)
        return run

    def test_offline_enable_persists_flag_without_unloading_foreign_live_module(self):
        # Positive control recreates the observed upstream side effect.
        REAL_COMMAND([sys.executable, self.fixture, "success"], allowed=(0, 1))
        self.assertTrue(self.proof.exists())
        self.proof.unlink(); self.state.write_text(self.initial)
        with patch.object(setup, "command", side_effect=self.transport("success")):
            self.instance.enable(self.source, self.revision)
        self.assertFalse(self.proof.exists())
        self.assertTrue(self.instance.repositories()[0][1]["hyprveil"]["enabled"])
        self.assertEqual(os.environ["HYPRLAND_INSTANCE_SIGNATURE"], "fixture-compositor", "isolation must be scoped to the child")

    def test_offline_return_one_does_not_hide_registration_or_build_failure(self):
        for mode in ("enable-failed", "failed-build", "wrong-revision"):
            with self.subTest(mode=mode):
                self.state.write_text(self.initial)
                with patch.object(setup, "command", side_effect=self.transport(mode)), self.assertRaises(setup.files.Refused):
                    self.instance.enable(self.source, self.revision)
                self.assertFalse(self.proof.exists())


class CacheReaderTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="hyprveil-manager-cache-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.path = self.directory / "state.toml"
        self.path.write_bytes(b"[state]\nhash='reviewed-abi'\n")

    def test_root_published_cache_is_readable_without_user_file_admission(self):
        original = setup.os.fstat
        def root_owned(fd):
            values = list(original(fd))
            values[4] = 0
            return os.stat_result(values)
        # Model the official manager's root-published inode ownership without
        # chown/sudo; actual file open/read/close and permissions remain real.
        with patch.object(setup.os, "fstat", side_effect=root_owned):
            self.assertEqual(setup.cache_read(self.path), self.path.read_bytes())

    def test_symlinks_hardlinks_fifo_and_writable_files_are_rejected(self):
        target = self.directory / "original"
        self.path.rename(target)
        for kind in ("symlink", "hardlink", "fifo", "writable"):
            with self.subTest(kind=kind):
                if kind == "symlink":
                    self.path.symlink_to(target)
                elif kind == "hardlink":
                    os.link(target, self.path)
                elif kind == "fifo":
                    os.mkfifo(self.path, 0o600)
                else:
                    self.path.write_bytes(b"unsafe")
                    self.path.chmod(0o666)
                with self.assertRaises((OSError, setup.files.Refused)):
                    setup.cache_read(self.path)
                self.path.unlink()

    def test_symlink_parent_and_writable_cache_directory_are_rejected(self):
        linked = self.directory / "linked"
        linked.symlink_to(self.directory, target_is_directory=True)
        with self.assertRaises(setup.files.Refused):
            setup.cache_read(linked / self.path.name)
        self.directory.chmod(0o777)
        with self.assertRaises(setup.files.Refused):
            setup.cache_read(self.path)
        self.directory.chmod(0o700)

    def test_foreign_owner_and_oversized_cache_file_are_rejected(self):
        original = setup.os.fstat
        def foreign(fd):
            values = list(original(fd))
            values[4] = max(os.getuid(), 0) + 1000
            return os.stat_result(values)
        with patch.object(setup.os, "fstat", side_effect=foreign), self.assertRaises(setup.files.Refused):
            setup.cache_read(self.path)
        with self.assertRaises(setup.files.Refused):
            setup.cache_read(self.path, limit=4)

    def test_cache_growth_during_read_is_still_bounded(self):
        self.path.write_bytes(b"abc")
        original = setup.os.read
        appended = False
        def growing(fd, size):
            nonlocal appended
            data = original(fd, size)
            if not appended:
                appended = True
                with self.path.open("ab") as handle:
                    handle.write(b"additional bytes exceeding limit")
            return data
        with patch.object(setup.os, "read", side_effect=growing), self.assertRaises(setup.files.Refused):
            setup.cache_read(self.path, limit=4)


if __name__ == "__main__":
    unittest.main()
