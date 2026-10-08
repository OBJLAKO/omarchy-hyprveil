# Contributing

Small, focused pull requests are welcome. Describe the behavior being
changed and the checks you ran. For security-sensitive problems, use
[private reporting](SECURITY.md) first.

The frontend requires native Hyprveil 0.4.0, but unit tests do not require a
running compositor. With Python 3, Node.js and Lua 5.4 installed, run from
the repository root:

```sh
python3 -m unittest discover -s tests -v
node plugin/tests/state.test.cjs
```

These are the checks in [CI](.github/workflows/tests.yml). Node tests also
execute Lua identity and state-change cases. Keep command arguments bounded,
preserve stable IDs as strings, and confirm native state after actions.
Background polling must preserve dirty drafts and steady control geometry.

With Omarchy and Quickshell installed, run the synthetic QML checks:

```sh
python3 plugin/tests/qml-smoke.py --native-config
python3 plugin/tests/qml-smoke.py --status-failure
python3 plugin/tests/qml-smoke.py --configure-failure
```

Pillow is additionally needed for color checks and documentation previews:

```sh
python3 plugin/tests/preview-colors.py
python3 assets/render-previews.py
```

Use synthetic windows and offscreen fixtures for shared test evidence.
Never add personal desktop captures, titles, session identifiers, local
absolute paths, binaries or runtime artifacts. Production source is in
`plugin/`; standalone installer helpers are in `tools/`. The
[native core](https://github.com/OBJLAKO/hyprveil) is a separate repository.
