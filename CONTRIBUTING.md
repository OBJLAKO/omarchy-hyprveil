# Contributing

Small, focused pull requests are welcome. Describe the behavior being
changed and the checks you ran. For security-sensitive problems, use
[private reporting](SECURITY.md) first.

The frontend requires native Hyprveil 0.5.0, but unit tests do not require a
running compositor. With Python 3, Node.js and Lua 5.4 installed, run from
the repository root:

```sh
python3 -m unittest discover -s tests -v
node tests/state.test.cjs
```

These are the checks in [CI](.github/workflows/tests.yml). Node tests also
execute Lua identity and state-change cases. Keep command arguments bounded,
preserve stable IDs as strings, and confirm native state after actions.
Background polling must preserve dirty drafts and steady control geometry.

With Omarchy and Quickshell installed, run the synthetic QML checks:

```sh
python3 tests/qml-smoke.py --native-config
python3 tests/qml-smoke.py --status-failure
python3 tests/qml-smoke.py --configure-failure
python3 tests/qml-smoke.py --presets
python3 tests/qml-process-failures.py
```

Pillow is additionally needed for color checks and documentation previews:

```sh
python3 tests/preview-colors.py
python3 assets/render-previews.py
```

Use synthetic windows and offscreen fixtures for shared test evidence.
Never add personal desktop captures, titles, session identifiers, local
absolute paths, binaries or runtime artifacts. QML, JavaScript, the watcher
and the single plugin manifest are at the repository root. Optional installer
helpers are in `tools/`; first-click setup is exposed by root `install.sh`.
Keep `native-release.json` pinned to a reviewed, published full core commit. The
[native core](https://github.com/OBJLAKO/hyprveil) is a separate repository.

Keep the permanent plugin ID `io.github.objlako.hyprveil`. A normal Omarchy
installation reads the root manifest and does not run a post-install hook.
Document new dependencies and file changes in the root README; installation
instructions for remote source must pin a full commit and fail closed before
execution. Do not present a local preflight as marketplace verification.
