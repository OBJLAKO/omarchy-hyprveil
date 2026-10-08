"""Small owned-file primitives for the standalone Omarchy installer.

There is no native plugin loader or Hyprland configuration writer here.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import uuid


class Refused(RuntimeError):
    pass


def directory(path, private=False):
    if path.resolve() != path:
        raise Refused("installation directory must not contain symlinks: " + str(path))
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    info = os.fstat(fd)
    if info.st_uid != os.getuid() or info.st_mode & 0o022 or private and stat.S_IMODE(info.st_mode) != 0o700:
        os.close(fd)
        raise Refused("installation directory has unsafe ownership or permissions: " + str(path))
    return fd


def ensure(path, private=False):
    if not path.exists():
        ensure(path.parent)
        path.mkdir(mode=0o700 if private else 0o755)
    os.close(directory(path, private))


def read_owned(path, limit=64 * 1024 * 1024):
    parent = directory(path.parent)
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1 or info.st_mode & 0o022 or info.st_size > limit:
            raise Refused("unsafe installation file: " + str(path))
        contents = bytearray()
        while chunk := os.read(fd, min(1024 * 1024, limit + 1 - len(contents))):
            contents.extend(chunk)
            if len(contents) > limit:
                raise Refused("oversized installation file: " + str(path))
        return bytes(contents), stat.S_IMODE(info.st_mode)
    finally:
        os.close(fd)


def atomic(path, contents, mode):
    parent = directory(path.parent)
    name = ".hyprveil-" + uuid.uuid4().hex + ".tmp"
    try:
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent)
        with os.fdopen(fd, "wb") as handle:
            handle.write(contents)
            handle.flush()
            os.fchmod(handle.fileno(), mode)
            os.fsync(handle.fileno())
        os.replace(name, path.name, src_dir_fd=parent, dst_dir_fd=parent)
        os.fsync(parent)
    finally:
        try:
            os.unlink(name, dir_fd=parent)
        except FileNotFoundError:
            pass
        os.close(parent)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def sha(contents):
    return hashlib.sha256(contents).hexdigest()


def controller_path(home):
    """Resolve only the documented per-user CLI, never an inherited PATH."""
    cli = home / ".local/bin/hyprveil"
    try:
        os.close(directory(cli.parent))
        info = cli.lstat()
    except FileNotFoundError as error:
        raise Refused("native Hyprveil CLI is missing; install ~/.local/bin/hyprveil first") from error
    target = cli
    if stat.S_ISLNK(info.st_mode):
        expected = home / ".local/share/hyprveil/controller.py"
        if info.st_uid != os.getuid() or os.readlink(cli) != str(expected):
            raise Refused("hyprveil CLI must point to its known per-user controller")
        target = expected
    elif not stat.S_ISREG(info.st_mode):
        raise Refused("hyprveil CLI must be an installed owned executable")
    _, mode = read_owned(target, 1024 * 1024)
    if not mode & 0o111:
        raise Refused("hyprveil CLI is not executable; install the native Hyprveil CLI first")
    return cli
