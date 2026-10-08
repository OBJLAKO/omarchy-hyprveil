#!/usr/bin/python3
"""Install the separate per-user Omarchy widget with private rollback copies."""
import argparse
import json
import os
from pathlib import Path
import tempfile

import files as install


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true", help="replace owned plugin files after private backups")
    args = parser.parse_args(argv)
    home = Path.home()
    controller = install.controller_path(home)
    source = Path(__file__).resolve().parents[1] / "plugin"
    plugins = home / ".config/omarchy/plugins"
    target = plugins / "sky.hyprveil"
    shell = home / ".config/omarchy/shell.json"
    before, mode = install.read_owned(shell, 1024 * 1024)
    config = json.loads(before)
    layout = config.get("bar", {}).get("layout")
    if not isinstance(layout, dict) or not isinstance(layout.get("right"), list):
        raise RuntimeError("existing shell layout is not recognized")
    files = {name: install.read_owned(source / name)[0] for name in
             ("BarWidget.qml", "Panel.qml", "StyleRow.qml", "Eye.qml", "State.js", "Privacy.js", "Appearance.js",
              "AppearanceEditor.qml", "SpoilerPreview.qml", "WindowPrivacy.qml", "privacy-watch", "README.md", "manifest.json")}
    if json.loads(files["manifest.json"])["id"] != "sky.hyprveil":
        raise RuntimeError("invalid shell plugin identity")
    install.ensure(plugins)
    previous = {}
    if os.path.lexists(target):
        os.close(install.directory(target))
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
    install.ensure(target)
    # Publish a new manifest only after its entry points exist.
    for name, contents in files.items():
        if name in previous and install.read_owned(target / name)[0] != previous[name]:
            raise RuntimeError("shell plugin changed during installation: " + name)
        if name not in previous and os.path.lexists(target / name):
            raise RuntimeError("new plugin file appeared during installation: " + name)
        install.atomic(target / name, contents, 0o755 if name == "privacy-watch" else 0o644)
    original_right = layout["right"]
    insertion = next((index for index, item in enumerate(original_right)
                      if isinstance(item, dict) and item.get("id") == "sky.screen-privacy"), 0)
    for section, values in layout.items():
        if isinstance(values, list):
            layout[section] = [item for item in values if not isinstance(item, dict) or item.get("id") != "sky.screen-privacy"]
    found = any(item.get("id") == "sky.hyprveil" for values in layout.values()
                if isinstance(values, list) for item in values if isinstance(item, dict))
    if not found:
        right = layout["right"]
        right.insert(min(insertion, len(right)), {"id": "sky.hyprveil"})
    if install.encoded(config) != install.encoded(json.loads(before)):
        if install.read_owned(shell, 1024 * 1024)[0] != before:
            raise RuntimeError("shell configuration changed during installation; widget installed but layout left untouched")
        install.atomic(shell, install.encoded(config), mode)
    report = {"installed": True, "plugin": str(target), "shell": str(shell),
              "controller": str(controller), "backup": str(backup / "shell.json"), "previous_shell_sha256": install.sha(before),
              "previous_files": {name: install.sha(contents) for name, contents in previous.items()},
              "files": {name: install.sha(contents) for name, contents in files.items()}}
    install.atomic(backup / "report.json", install.encoded(report), 0o600)
    print(json.dumps(report, ensure_ascii=False))
    return report


if __name__ == "__main__":
    main()
