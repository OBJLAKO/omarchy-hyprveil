#!/usr/bin/python3
"""Install the separate per-user Omarchy widget with private rollback copies."""
import argparse
import json
import os
from pathlib import Path
import tempfile

import files as install

PLUGIN_ID = "io.github.objlako.hyprveil"
LEGACY_IDS = ("sky.hyprveil", "sky.screen-privacy")
RUNTIME_FILES = ("BarWidget.qml", "Panel.qml", "StyleRow.qml", "Eye.qml", "State.js", "I18n.js", "Privacy.js", "Appearance.js",
                 "AppearanceEditor.qml", "SpoilerPreview.qml", "WindowPrivacy.qml", "privacy-watch", "README.md", "manifest.json")

def entry_id(item):
    return item.get("id") if isinstance(item, dict) else item if isinstance(item, str) else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true", help="replace owned plugin files after private backups")
    args = parser.parse_args(argv)
    home = Path.home()
    controller = install.controller_path(home)
    source = Path(__file__).resolve().parents[1]
    plugins = home / ".config/omarchy/plugins"
    target = plugins / PLUGIN_ID
    shell = home / ".config/omarchy/shell.json"
    before, mode = install.read_owned(shell, 1024 * 1024)
    config = json.loads(before)
    layout = config.get("bar", {}).get("layout")
    if not isinstance(layout, dict) or not isinstance(layout.get("right"), list):
        raise RuntimeError("existing shell layout is not recognized")
    files = {name: install.read_owned(source / name)[0] for name in RUNTIME_FILES}
    if json.loads(files["manifest.json"])["id"] != PLUGIN_ID:
        raise RuntimeError("invalid shell plugin identity")
    legacy_entries = any(entry_id(item) in LEGACY_IDS
                         for values in layout.values() if isinstance(values, list) for item in values)
    legacy_target = plugins / "sky.hyprveil"
    if (legacy_entries or os.path.lexists(legacy_target)) and not args.update:
        raise RuntimeError("legacy Hyprveil installation detected; use --update for an explicit backed-up migration")
    legacy_previous = {}
    if os.path.lexists(legacy_target):
        os.close(install.directory(legacy_target))
        for name in RUNTIME_FILES:
            if os.path.lexists(legacy_target / name):
                legacy_previous[name] = install.read_owned(legacy_target / name)[0]
    install.ensure(plugins)
    previous = {}
    if os.path.lexists(target):
        os.close(install.directory(target))
        if os.path.lexists(target / ".git"):
            raise RuntimeError("plugin is Git-managed; use: omarchy plugin update " + PLUGIN_ID)
        for name, contents in files.items():
            if os.path.lexists(target / name):
                previous[name] = install.read_owned(target / name)[0]
                if previous[name] != contents and not args.update:
                    raise RuntimeError("existing shell plugin differs; use --update for a backed-up replacement: " + name)
    artifacts = Path(__file__).resolve().parents[1] / "artifacts"
    install.ensure(artifacts)
    backup = Path(tempfile.mkdtemp(prefix="shell-install-", dir=artifacts))
    backup.chmod(0o700)
    install.atomic(backup / "shell.json", before, 0o600)
    for name, contents in previous.items():
        install.atomic(backup / name, contents, 0o600)
    if legacy_previous:
        legacy_backup = backup / "legacy-sky.hyprveil"
        install.ensure(legacy_backup, private=True)
        for name, contents in legacy_previous.items():
            install.atomic(legacy_backup / name, contents, 0o600)
    install.ensure(target)
    # Publish a new manifest only after its entry points exist.
    for name, contents in files.items():
        if name in previous and install.read_owned(target / name)[0] != previous[name]:
            raise RuntimeError("shell plugin changed during installation: " + name)
        if name not in previous and os.path.lexists(target / name):
            raise RuntimeError("new plugin file appeared during installation: " + name)
        install.atomic(target / name, contents, 0o755 if name == "privacy-watch" else 0o644)
    # Retain the existing new entry and its placement/settings when present.
    # Otherwise migrate the first legacy entry in place. Old directories and
    # helper files remain intact for existing keybindings.
    found = any(entry_id(item) == PLUGIN_ID
                for values in layout.values() if isinstance(values, list) for item in values)
    migrated = False
    kept_new = False
    for section, values in layout.items():
        if isinstance(values, list):
            output = []
            for item in values:
                if entry_id(item) == PLUGIN_ID:
                    if not kept_new:
                        output.append(item)
                        kept_new = True
                elif entry_id(item) in LEGACY_IDS:
                    if not found and not migrated:
                        replacement = dict(item) if isinstance(item, dict) and item["id"] == "sky.hyprveil" else {}
                        replacement["id"] = PLUGIN_ID
                        output.append(replacement)
                        migrated = True
                else:
                    output.append(item)
            layout[section] = output
    if not found and not migrated:
        layout["right"].insert(0, {"id": PLUGIN_ID})
    if install.encoded(config) != install.encoded(json.loads(before)):
        if install.read_owned(shell, 1024 * 1024)[0] != before:
            raise RuntimeError("shell configuration changed during installation; widget installed but layout left untouched")
        install.atomic(shell, install.encoded(config), mode)
    report = {"installed": True, "plugin": str(target), "shell": str(shell),
              "controller": str(controller), "backup": str(backup / "shell.json"), "previous_shell_sha256": install.sha(before),
              "legacy_files": {name: install.sha(contents) for name, contents in legacy_previous.items()},
              "previous_files": {name: install.sha(contents) for name, contents in previous.items()},
              "files": {name: install.sha(contents) for name, contents in files.items()}}
    install.atomic(backup / "report.json", install.encoded(report), 0o600)
    print(json.dumps(report, ensure_ascii=False))
    return report


if __name__ == "__main__":
    main()
