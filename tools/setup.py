#!/usr/bin/python3
"""First-click Hyprpm setup, selective activation and conservative removal."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import pwd
import re
import selectors
import signal
import time
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent if HERE.name == "tools" else HERE
sys.path.insert(0, str(SOURCE))
import native_cli
import native_service as service
import files

REPOSITORY = "https://github.com/OBJLAKO/hyprveil"
BEGIN = "-- BEGIN OMARCHY HYPRVEIL SETUP v1"
END = "-- END OMARCHY HYPRVEIL SETUP v1"
BLOCK = BEGIN + '\ndofile(os.getenv("HOME") .. "/.config/hypr/hyprveil-hyprpm.lua")\n' + END
BUILD_PACKAGES = ("base-devel", "cmake", "meson", "cpio", "pkgconf", "git")
HELPERS = ("setup.py", "files.py", "native_cli.py", "native_service.py", "uninstall.sh")


class PendingLogin(files.Refused):
    """Prepared startup permissions have not yet admitted the native plugin."""


def foreground(fd, group):
    # The waiting parent is briefly a background process when restoring its
    # terminal; block SIGTTOU only around that terminal ownership operation.
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTTOU})
    try:
        os.tcsetpgrp(fd, group)
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


def command(argv, *, capture=False, cwd=None, timeout=1800, allowed=(0,)):
    """Bound output, own the whole process group and preserve interactive sudo."""
    env = {key: value for key, value in os.environ.items() if key in
           ("HOME", "USER", "LOGNAME", "XDG_RUNTIME_DIR", "HYPRLAND_INSTANCE_SIGNATURE", "WAYLAND_DISPLAY", "DISPLAY", "TERM", "COLORTERM")}
    env.update(PATH="/usr/bin:/bin", LANG="C.UTF-8", PYTHONNOUSERSITE="1")
    args = list(map(str, argv))
    print("+ " + " ".join(args), flush=True)
    process = subprocess.Popen(args, cwd=cwd, env=env, process_group=0,
                               stdout=subprocess.PIPE if capture else None,
                               stderr=subprocess.PIPE if capture else None)
    tty, original_group = None, None
    streams = {}
    selector = selectors.DefaultSelector()
    try:
        if not capture and sys.stdin.isatty():
            tty = sys.stdin.fileno()
            original_group = os.tcgetpgrp(tty)
            foreground(tty, process.pid)
            # A fast reader may have reached the terminal before the parent
            # could hand it over and received SIGTTIN. Resume only our group.
            try:
                os.killpg(process.pid, signal.SIGCONT)
            except ProcessLookupError:
                pass  # A short command may already have exited.
        if capture:
            streams = {process.stdout: bytearray(), process.stderr: bytearray()}
            for pipe in streams:
                os.set_blocking(pipe.fileno(), False)
                selector.register(pipe, selectors.EVENT_READ)
            deadline = time.monotonic() + timeout
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(args, timeout)
                for key, _ in selector.select(min(remaining, 0.1)):
                    chunk = os.read(key.fd, 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        streams[key.fileobj].extend(chunk)
                        if sum(map(len, streams.values())) > 131072:
                            raise files.Refused("oversized setup command output")
            process.wait(timeout=max(0.001, deadline - time.monotonic()))
        else:
            process.wait(timeout=timeout)
        stdout = streams[process.stdout].decode("utf-8") if capture else None
        stderr = streams[process.stderr].decode("utf-8") if capture else None
        if process.returncode not in allowed:
            raise subprocess.CalledProcessError(process.returncode, args, stdout, stderr)
        return stdout if capture else ""
    finally:
        # Killing the group also closes inherited pipe descriptors in compiler
        # grandchildren; terminating only Hyprpm would leave a live build.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        if tty is not None:
            foreground(tty, original_group)
        selector.close()
        for pipe in streams:
            pipe.close()


def read_optional(path, limit=2 * 1024 * 1024):
    if not os.path.lexists(path):
        return None
    return files.read_owned(path, limit)[0]


def cache_dir(path):
    """Hyprpm publishes root-owned 0755 cache directories, unlike user config."""
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise files.Refused("Hyprpm cache directory must not contain symlinks: " + str(path))
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    info = os.fstat(fd)
    if info.st_uid not in (0, os.getuid()) or info.st_mode & 0o022:
        os.close(fd)
        raise files.Refused("unsafe Hyprpm cache directory: " + str(path))
    return fd


def cache_read(path, limit=64 * 1024 * 1024):
    """Read bounded single-link regular manager state/binaries; never mutate it."""
    path = Path(path)
    parent = cache_dir(path.parent)
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid not in (0, os.getuid()) or info.st_nlink != 1 or info.st_mode & 0o022 or info.st_size > limit:
            raise files.Refused("unsafe Hyprpm cache file: " + str(path))
        contents = bytearray()
        while chunk := os.read(fd, min(1024 * 1024, limit + 1 - len(contents))):
            contents.extend(chunk)
            if len(contents) > limit:
                raise files.Refused("oversized Hyprpm cache file: " + str(path))
        return bytes(contents)
    finally:
        os.close(fd)


def digest(path):
    data = read_optional(path)
    return files.sha(data) if data is not None else None


def ask(question):
    if not sys.stdin.isatty():
        return False
    return input(question + " [y/N] ").strip().lower() in ("y", "yes")


def release():
    value = json.loads(files.read_owned(SOURCE / "native-release.json", 8192)[0])
    if set(value) != {"repository", "revision", "version"} or value["repository"] != REPOSITORY or value["version"] != "0.5.0" or not re.fullmatch(r"[0-9a-f]{40}", value["revision"]):
        raise files.Refused("invalid reviewed native release pin")
    return value


class Setup:
    def __init__(self, home=None, cache=None):
        self.home = Path.home() if home is None else Path(home)
        self.dest = self.home / ".local/share/omarchy-hyprveil"
        self.conf = self.home / ".config/omarchy-hyprveil"
        self.hypr = self.home / ".config/hypr"
        self.main = self.hypr / "hyprland.lua"
        self.settings = self.hypr / "hyprveil-settings.lua"
        self.bootstrap = self.hypr / "hyprveil-hyprpm.lua"
        self.receipt = self.conf / "install.json"
        self.cache = Path(cache) if cache is not None else Path("/var/cache/hyprpm") / pwd.getpwuid(os.getuid()).pw_name
        self.backup = None
        self.saved = {}
        self.written = {}

    def old_receipt(self):
        data = read_optional(self.receipt, 128 * 1024)
        if data is None:
            return {"files": {}, "block_sha256": None}
        value = json.loads(data)
        if not isinstance(value, dict) or value.get("schema") != 1 or not isinstance(value.get("files"), dict):
            raise files.Refused("unrecognized setup record; left untouched")
        allowed = {str(self.dest / name) for name in HELPERS} | {str(self.bootstrap)}
        if not isinstance(value.get("native_source"), str) or not isinstance(value.get("native_revision"), str) or type(value.get("native_owned")) is not bool or value.get("version") != "0.5.0" or len(value["native_revision"]) > 256 or (value["native_owned"] and not re.fullmatch(r"[0-9a-f]{40}", value["native_revision"])):
            raise files.Refused("invalid native ownership record")
        if not set(value["files"]).issubset(allowed) or any(not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha) for sha in value["files"].values()) or not isinstance(value.get("block_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", value["block_sha256"]):
            raise files.Refused("unsafe setup record")
        return value

    def legacy_guard(self):
        if os.path.lexists(self.hypr / "hyprveil.lua"):
            raise files.Refused("legacy Hyprveil loader exists: complete the cold-login migration in docs/GUIDE.md first")
        for path in self.hypr.glob("*.lua"):
            text = files.read_owned(path, 2 * 1024 * 1024)[0].decode()
            if "BEGIN HYPRVEIL MANAGED AUTOLOAD" in text or re.search(r'(?:controller\.py|\.local/bin/hyprveil)\s+(?:start|enable)', text):
                raise files.Refused("legacy Hyprveil autoload in " + str(path) + "; migrate it before setup")

    def repositories(self):
        result = []
        if not os.path.lexists(self.cache):
            return result
        os.close(cache_dir(self.cache))
        for state in sorted(self.cache.glob("*/state.toml")):
            data = tomllib.loads(cache_read(state, 128 * 1024).decode())
            if "hyprveil" in data:
                result.append((state.parent, data))
        if len(result) > 1:
            raise files.Refused("multiple Hyprpm repositories provide Hyprveil; choose one manually")
        return result

    def state(self):
        controller = native_cli.Controller()
        state = controller.run("status")
        if state["loaded"]:
            plugins = controller.plugins()
            if len(plugins) != 1 or plugins[0].get("version") != "0.5.0":
                raise files.Refused("loaded Hyprveil is not version 0.5.0; complete the cold-login migration before setup")
        return state

    def preflight(self):
        if not os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
            raise files.Refused("run setup inside your Hyprland session")
        self.legacy_guard()
        files.read_owned(self.main, 2 * 1024 * 1024)
        version = json.loads(command(["hyprctl", "version", "-j"], capture=True, timeout=20))
        if not isinstance(version, dict) or version.get("abiHash") != service.TESTED_ABI:
            raise files.Refused("this release requires the reviewed Hyprland 0.56.2 build; other ABIs are refused")
        errors = command(["hyprctl", "configerrors"], capture=True, timeout=20).strip()
        if errors:
            raise files.Refused("fix existing Hyprland config errors before setup: " + errors[:1024])
        return version

    def write(self, path, data, mode=0o644):
        before = read_optional(path)
        files.ensure(path.parent)
        if before is not None and before != data:
            relative = path.relative_to(self.home)
            target = self.backup / relative
            files.ensure(target.parent, private=True)
            files.atomic(target, before, 0o600)
        self.saved.setdefault(path, (before, files.read_owned(path)[1] if before is not None else mode))
        # Recheck immediately before replace; never overwrite a concurrent edit.
        if read_optional(path) != before:
            raise files.Refused("file changed during setup: " + str(path))
        files.atomic(path, data, mode)
        self.written[path] = files.sha(data)

    def rollback(self):
        if self.main in self.written and digest(self.main) != self.written[self.main]:
            # The user's retained main config can now reference every runtime
            # file just installed. Keep that coherent set rather than creating
            # dangling dofile/startup paths while preserving the user's edit.
            print("Kept your edited main config and its complete native helper/settings; rerun setup to finish. Native Hyprpm state remains installed.", file=sys.stderr)
            return
        for path, (before, mode) in reversed(list(self.saved.items())):
            if digest(path) != self.written.get(path):
                print("Kept concurrent edit during rollback: " + str(path), file=sys.stderr)
                continue
            if before is None:
                if path.exists():
                    path.unlink()
            else:
                files.atomic(path, before, mode)

    def source(self, pin, local=None):
        target = self.dest / ("native-" + pin["revision"])
        if local is not None:
            target = Path(local).absolute()
            os.close(files.directory(target))
        elif not os.path.lexists(target):
            files.ensure(self.dest)
            temporary = Path(tempfile.mkdtemp(prefix="native-fetch-", dir=self.dest))
            try:
                command(["git", "init", "-q", "-b", "main", temporary])
                command(["git", "-C", temporary, "fetch", "--depth=1", REPOSITORY, pin["revision"]])
                command(["git", "-C", temporary, "checkout", "-q", "-B", "main", "FETCH_HEAD"])
                temporary.rename(target)
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)
        os.close(files.directory(target))
        actual = command(["git", "-C", target, "rev-parse", "HEAD"], capture=True).strip()
        dirty = command(["git", "-C", target, "status", "--porcelain", "--untracked-files=all"], capture=True).strip()
        if actual != pin["revision"] or dirty:
            raise files.Refused("native source must be the exact clean reviewed commit")
        command(["git", "-C", target, "fsck", "--no-progress", "--no-dangling"], capture=True)
        manifest = tomllib.loads(files.read_owned(target / "hyprpm.toml", 8192)[0].decode())
        if manifest.get("repository", {}).get("name") != "hyprveil" or set(manifest) != {"repository", "hyprveil"}:
            raise files.Refused("unexpected native Hyprpm manifest")
        return target

    def activate(self):
        state = self.state()
        if state["loaded"]:
            # A second loader can win the login race after the guarded Lua
            # settings pass. Apply saved settings on this path as well.
            native_cli.Controller().run("reload-config")
            return self.state()
        repositories = self.repositories()
        if len(repositories) != 1:
            raise files.Refused("Hyprpm has no built Hyprveil repository")
        folder, data = repositories[0]
        plugin = data["hyprveil"]
        if not isinstance(plugin, dict) or plugin.get("filename") != "hyprveil.so" or plugin.get("enabled") is not True or plugin.get("failed") is not False:
            raise files.Refused("Hyprpm has not enabled a successful Hyprveil build")
        path = folder / "hyprveil.so"
        cache_read(path)  # manager publishes root-owned binaries; refuse links/writable files
        # Never use hyprpm reload: it unloads unrelated manually loaded modules.
        command(["hyprctl", "plugin", "load", path], timeout=30)
        state = self.state()
        if not state["loaded"]:
            raise PendingLogin("setup prepared; log out and back in for Hyprland plugin permission. Protection is NOT active yet. Native source, startup helper and settings were kept; inspect the terminal output if loading still fails after login")
        native_cli.Controller().run("reload-config")
        return self.state()

    def rebuild(self, pin, source, old, folder, need_headers):
        # Prove that the recovery source still exists before removing a build.
        self.source(dict(pin, revision=old["native_revision"]), old["native_source"])
        if self.state()["loaded"]:
            raise files.Refused("Hyprveil loaded during setup; kept its current build and protection")
        try:
            command(["hyprpm", "remove", folder.name])
            if need_headers:
                command(["hyprpm", "update"])
            command(["hyprpm", "add", source, pin["revision"]])
            command(["hyprpm", "enable", "hyprveil"])
        except (Exception, KeyboardInterrupt) as failure:
            try:
                # A failed enable can leave the new repository registered.
                # Remove only that exact replacement before restoring the old.
                replacement = self.repositories()
                preserved = False
                if replacement:
                    current, metadata = replacement[0]
                    repo = metadata.get("repository", {})
                    preserved = (current.name == "hyprveil" and repo.get("url") == old["native_source"]
                                 and repo.get("rev") == old["native_revision"]
                                 and metadata.get("hyprveil", {}).get("failed") is False
                                 and metadata.get("hyprveil", {}).get("enabled") is True)
                    if not preserved:
                        if current.name != "hyprveil" or repo.get("url") != str(source):
                            raise files.Refused("repository changed during rebuild; left it untouched")
                        if self.state()["loaded"]:
                            raise files.Refused("Hyprveil loaded during recovery; kept its protection")
                        command(["hyprpm", "remove", current.name])
                if not preserved:
                    command(["hyprpm", "add", old["native_source"], old["native_revision"]])
                    command(["hyprpm", "enable", "hyprveil"])
            except Exception as recovery:
                raise files.Refused("rebuild failed and the previous Hyprpm registration could not be restored; "
                                    "native source/settings were kept. Inspect the terminal output and restore with "
                                    "the original Hyprpm workflow: " + str(recovery)) from failure
            raise

    def install(self, args):
        pin = release()
        version = self.preflight()
        old = self.old_receipt()
        before = files.read_owned(self.main)[0].decode()
        if before.count(BEGIN) != before.count(END) or before.count(BEGIN) > 1:
            raise files.Refused("ambiguous setup block in hyprland.lua")
        if BEGIN in before and old.get("block_sha256") != files.sha(BLOCK.encode()):
            raise files.Refused("unrecognized setup block; left untouched")
        if BEGIN in before:
            if before[before.index(BEGIN):before.index(END) + len(END)] != BLOCK:
                raise files.Refused("setup block was edited; left untouched")
        if os.path.lexists(self.settings):
            service.parse_lua_settings(files.read_owned(self.settings)[0])
        existing = self.repositories()
        state = self.state()
        metadata = existing[0][1].get("repository", {}) if existing else {}
        owned = bool(existing and existing[0][0].name == "hyprveil" and metadata.get("name") == "hyprveil" and
                     old.get("native_owned") is True and metadata.get("url") == old.get("native_source") and
                     metadata.get("rev") == old.get("native_revision"))
        repair = bool(existing and owned and not state["loaded"])
        if args.plugin_only and existing and not owned:
            raise files.Refused("Hyprveil was installed outside this setup; rebuild it with its original Hyprpm workflow")
        global_path = self.cache / "state.toml"
        global_state = cache_read(global_path, 128 * 1024) if os.path.lexists(global_path) else None
        headers = tomllib.loads(global_state.decode()) if global_state else {}
        if not isinstance(headers.get("state", {}), dict):
            raise files.Refused("invalid Hyprpm global header state")
        need_headers = headers.get("state", {}).get("hash") != version["abiHash"]
        if not need_headers:
            try:
                cache_read(self.cache / "headersRoot/share/pkgconfig/hyprland.pc", 128 * 1024)
            except FileNotFoundError:
                need_headers = True
        print("\nHyprveil setup will:\n  - build the reviewed native plugin with hyprpm (build tools/headers may ask for sudo)\n  - add a marked startup block and persistent appearance settings\n  - keep private backups and install an independent uninstaller\n  - activate only Hyprveil; other loaded plugins are left alone\nStop screen sharing before setup or rebuild.\n")
        if not args.yes and not ask("Set up Hyprveil?" if not args.plugin_only else "Rebuild Hyprveil?"):
            raise files.Refused("setup cancelled; nothing changed (use --yes for unattended setup)")
        if need_headers and (not existing or repair) and not args.hyprpm_update:
            print("Hyprpm headers need updating. `hyprpm update` also rebuilds every other Hyprpm repository.")
            if not ask("Allow hyprpm update?"):
                raise files.Refused("headers need updating; use --hyprpm-update only after reviewing its scope")
        if args.plugin_only and state["loaded"]:
            raise files.Refused("Hyprveil is already loaded; cold-log in before rebuilding, to keep current protection")
        files.ensure(self.conf)
        self.backup = Path(tempfile.mkdtemp(prefix="backup-", dir=self.conf))
        self.backup.chmod(0o700)
        if not existing:
            packages = command(["pacman", "-T", *BUILD_PACKAGES], capture=True, timeout=20, allowed=(0, 127)) if shutil.which("pacman") else ""
            missing = packages.splitlines()
            if missing:
                # pacman -T exits127 when missing; handled by missing_packages below.
                command(["sudo", "pacman", "-S", "--needed", *missing])
            source = self.source(pin, args.core_source)
            if need_headers:
                command(["hyprpm", "update"])
            command(["hyprpm", "add", source, pin["revision"]])
        elif repair:
            folder, metadata = existing[0]
            source = self.source(pin, args.core_source)
            self.rebuild(pin, source, old, folder, need_headers)
        else:
            source = metadata.get("url", "")
        if not repair:
            command(["hyprpm", "enable", "hyprveil"])
        try:
            payloads = {}
            for name in HELPERS:
                original = HERE / name if name in ("setup.py", "files.py") else SOURCE / name
                payloads[self.dest / name] = files.read_owned(original)[0]
            helper_command = "/usr/bin/python3 " + shlex.quote(str(self.dest / "setup.py")) + " --load-only"
            bootstrap = ('-- Omarchy Hyprveil: selective native activation; no global hyprpm reload.\n'
                         'hl.permission("^/usr/(bin|local/bin)/hyprctl$", "plugin", "allow")\n'
                         'dofile(' + service.lua_string(str(self.settings)) + ')\n'
                         'hl.on("hyprland.start", function()\n'
                         '  hl.exec_cmd(' + service.lua_string(helper_command) + ')\n'
                         'end)\n').encode()
            payloads[self.bootstrap] = bootstrap
            for path, contents in payloads.items():
                self.write(path, contents, 0o755 if path.name == "uninstall.sh" else 0o644)
            if not os.path.lexists(self.settings):
                values = dict(mode="spoiler", image_path="", **service.DEFAULT_APPEARANCE)
                contents = (service.lua_settings_block(values) + '\n\nlocal _, missing = hl.get_config("plugin.hyprveil.mode")\nif not missing then hl.config({ plugin = { hyprveil = hyprveil_settings } }) end\n').encode()
                self.write(self.settings, contents)
            else:
                service.parse_lua_settings(files.read_owned(self.settings)[0])
            if BEGIN in before:
                start, stop = before.index(BEGIN), before.index(END) + len(END)
                if before[start:stop] != BLOCK:
                    raise files.Refused("setup block was edited; left untouched")
                after = before
            else:
                after = before.rstrip() + "\n\n" + BLOCK + "\n"
            if files.read_owned(self.main)[0].decode() != before:
                raise files.Refused("hyprland.lua changed during the build; kept your edit")
            self.write(self.main, after.encode(), files.read_owned(self.main)[1])
            command(["hyprctl", "reload"], timeout=30)
            errors = command(["hyprctl", "configerrors"], capture=True, timeout=20).strip()
            if errors:
                raise files.Refused("configuration rejected: " + errors[:1024])
            record = {"schema": 1, "files": {str(path): files.sha(data) for path, data in payloads.items()},
                      "block_sha256": files.sha(BLOCK.encode()), "native_source": str(source),
                      "native_revision": pin["revision"] if not existing or repair else metadata.get("rev", ""),
                      "native_owned": not existing or owned, "version": pin["version"], "pending_login": True}
            self.write(self.receipt, files.encoded(record), 0o600)
            self.activate()
            record["pending_login"] = False
            self.write(self.receipt, files.encoded(record), 0o600)
        except PendingLogin:
            # Startup permissions can take effect only after a new session.
            # Preserve the complete, recoverable setup, but never claim ready.
            raise
        except (Exception, KeyboardInterrupt):
            self.rollback()
            command(["hyprctl", "reload"], timeout=30)
            raise
        print("Hyprveil ready. Left click protects the focused window; right click opens appearance.\nUninstall: " + str(self.dest / "uninstall.sh"))

    def uninstall(self):
        # This package is a UI companion. Removing a working native loader
        # would silently drop next-login protection, so it stays independent.
        self.old_receipt()
        command(["omarchy", "plugin", "remove", "io.github.objlako.hyprveil"])
        print("Removed the Omarchy widget. Native Hyprveil, its selective startup helper, settings and private backups remain.")
        print("Current and next-login protection continue. Native removal is an explicit separate Hyprpm operation; stop sharing first.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", "-y", action="store_true")
    parser.add_argument("--plugin-only", action="store_true")
    parser.add_argument("--hyprpm-update", action="store_true")
    parser.add_argument("--core-source", type=Path, help="use an exact clean local copy of the pinned native revision")
    parser.add_argument("--load-only", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args(argv)
    setup = Setup()
    # One process owns every setup/update/uninstall transaction. No overlap.
    try:
        if not args.uninstall and not args.yes and not sys.stdin.isatty():
            if not args.load_only:
                raise files.Refused("no terminal to ask in; nothing changed (run install.sh in a terminal, or pass --yes)")
        files.ensure(setup.conf)
        lock = setup.conf / ".lock"
        fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise files.Refused("unsafe setup lock")
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if args.load_only:
                setup.activate()
            else:
                setup.uninstall() if args.uninstall else setup.install(args)
        finally:
            os.close(fd)
        return 0
    except KeyboardInterrupt:
        print("Hyprveil setup cancelled. Inspect the terminal output for retained native manager state.", file=sys.stderr)
        return 130
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, service.Refused) as error:
        print("Hyprveil: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
