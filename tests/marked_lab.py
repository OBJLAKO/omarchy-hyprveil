"""Read-only admission to an already-running, explicitly marked nested lab.

This repository does not launch compositors or import native Hyprveil source.
"""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import re
import stat

loader = importlib.machinery.SourceFileLoader("qml_privacy_watch", str(Path(__file__).resolve().parents[1] / "privacy-watch"))
spec = importlib.util.spec_from_loader(loader.name, loader)
watch = importlib.util.module_from_spec(spec)
loader.exec_module(watch)


def proc_env(pid):
    with Path(f"/proc/{pid}/environ").open("rb") as handle:
        contents = handle.read(262145)
    if len(contents) > 262144:
        raise watch.Refused("oversized lab environment")
    return dict(item.split(b"=", 1) for item in contents.split(b"\0") if b"=" in item)


def load_lab(path):
    runtime = Path(path).absolute()
    if runtime.resolve(strict=True) != runtime or runtime.parent != Path("/tmp") or not runtime.name.startswith(("hv-", "hyprveil-lab-")):
        raise watch.Refused("lab must be an explicit private directory directly under /tmp")
    watch.identity(runtime, directory=True)
    fd = os.open(runtime / ".hyprveil-lab", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1:
            raise watch.Refused("invalid lab marker")
        contents = os.read(fd, 4097)
    finally:
        os.close(fd)
    if len(contents) > 4096:
        raise watch.Refused("oversized lab marker")
    data = json.loads(contents, object_pairs_hook=watch.unique_object)
    if not isinstance(data, dict) or data.get("runtime_dir") != str(runtime) or type(data.get("pid")) is not int or data["pid"] <= 0:
        raise watch.Refused("invalid isolated lab identity")
    signature = watch.validate_signature(data.get("signature"))
    display = data.get("wayland_display")
    if not isinstance(display, str) or not re.fullmatch(r"wayland-[0-9]+", display) or signature == data.get("parent_signature"):
        raise watch.Refused("invalid isolated display")
    watch.identity(runtime / display)
    with_session = watch.BoundSession(runtime, signature, lab=True)
    try:
        if with_session.target[0] != data["pid"]:
            raise watch.Refused("lab marker and compositor peer disagree")
        env = proc_env(data["pid"])
        if env.get(b"XDG_RUNTIME_DIR") != str(runtime).encode() or env.get(b"HYPRVEIL_LAB_RUNTIME") != str(runtime).encode() or env.get(b"LIBSEAT_BACKEND") != b"hyprveil-disabled":
            raise watch.Refused("marked compositor is not isolated from physical seats")
        with_session.verify()
    finally:
        with_session.close()
    return runtime, data


def lab_env(runtime, data):
    env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}
    env.update(XDG_RUNTIME_DIR=str(runtime), WAYLAND_DISPLAY=data["wayland_display"],
               HYPRLAND_INSTANCE_SIGNATURE=data["signature"], GDK_BACKEND="wayland",
               HOME=str(runtime / "home"), XDG_CONFIG_HOME=str(runtime / "home/.config"),
               XDG_CACHE_HOME=str(runtime / "home/.cache"), XDG_DATA_HOME=str(runtime / "home/.local/share"),
               HYPRVEIL_LAB_RUNTIME=str(runtime))
    return env
