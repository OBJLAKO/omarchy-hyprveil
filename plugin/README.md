# Hyprveil panel guide

This Omarchy widget controls [native Hyprveil](https://github.com/OBJLAKO/hyprveil)
through its installed CLI and public Lua API. It requires the 0.4.0 native
API; the core's tested Hyprland version is 0.56.2. The widget does not build
or install native code. Its stable Omarchy plugin ID is `sky.hyprveil`.

## Installation

Install native Hyprveil first. From the root of
[omarchy-hyprveil](https://github.com/OBJLAKO/omarchy-hyprveil):

```sh
python3 tools/install.py
```

The installer resolves only `~/.local/bin/hyprveil`: an owned executable or
the native installer's exact symlink to
`~/.local/share/hyprveil/controller.py`. It does not search PATH or run the
controller during installation. It creates the user plugin directory when
needed and installs the widget into
`~/.config/omarchy/plugins/sky.hyprveil`.

Existing files and `~/.config/omarchy/shell.json` get private backup copies
under `artifacts/shell-install-*` in the checkout. The printed report lists
paths and hashes. Updates that replace changed files require:

```sh
python3 tools/install.py --update
```

The installer adds one widget entry, preserves unrelated layout and
keybindings, and removes the superseded legacy eye entry if present.
Existing helper files are retained. It refuses links, FIFOs, unsafe file
ownership/permissions and detected concurrent changes. A concurrent layout
edit is left untouched; widget files may already have been installed.

Omarchy hot-reloads these user files. Neither Hyprland nor native Hyprveil
is restarted by this installer. To restore a layout manually, use the
reported `shell.json` backup after checking it against any later edits.
Previous widget files are beside that backup. Retain their original
permissions; `privacy-watch` must be executable.

## Controls

- **Left or middle click** toggles the focused window's capture privacy.
- **Right click** opens the panel. The panel also has a Show/Hide button.
- An **open muted eye** means visible in capture; a **crossed accent eye**
  means hidden. A question mark means unconfirmed state.
- Inherited protection disables the Show/Hide button. A child window may
  inherit protection from a parent, including retained protection after
  that parent closes.

The native API checks the clicked address and stable identity against the
focused window atomically. A focus change or recycled address is refused.
Repeated Hide requests leave an already-hidden window hidden. The icon
follows the watcher's actual confirmation, not an optimistic command result.
Keyboard shortcuts for native Hyprveil are configured separately in Hyprland.

## Capture styles

| Panel label | Mode | Meaning |
| :--- | :--- | :--- |
| Спойлер | `spoiler` | An opaque procedural mask with satin or Telegram appearance. |
| Полностью скрыть | `omit` | Exclude the protected window from compositor capture. |
| Обычная маска | `black` | A plain black mask. |
| Вернуть исходное скрытие | `omit` | Return to omission while Hyprveil stays loaded. |

Style changes preserve which windows are private. Your own desktop keeps
its normal window contents. The panel can load the installed native plugin
when it is not loaded; style controls stay disabled until state is confirmed.

## Appearance and native settings

The Оформление tab exposes seven fields:

| Field | Range/default |
| :--- | :--- |
| Variant | Satin / Telegram; satin by default |
| Color | Opaque `#RRGGBB`; white by default |
| Grain | 0–100%; default 50% |
| Speed | 0–200%; default 100%; 0 pauses the pattern |
| Darkness | 0–100%; default 50% |
| Eye | On/off; on by default |
| Eye size | 40–128 px; default 80 px |

The preview is procedural and never samples client pixels. Color and
darkness keep the mask opaque. Apply saves after a native acknowledgement
and a fresh status check. Variant buttons apply immediately while keeping
other parameters. Reset appearance restores defaults and keeps the hiding
mode. When Black or Omit is selected, these parameters take effect after
selecting Spoiler.

The confirmed native mode and appearance determine the controls. Old
installation preferences do not override actual native state. Settings are
saved to the managed literal block in
`~/.config/hypr/hyprveil-settings.lua`. Custom Lua belongs outside that block
and is preserved. Custom code inside it or a later override can cause a
GUI save to be refused; the panel keeps the draft and reports the result.

**Перечитать Lua** explicitly reloads configuration and confirms the native
result. It preserves an unsaved draft; clean fields follow the new state.
The separate refresh control reads current status without reloading Lua.
Normal polling runs every 2.5 seconds only while the panel is open. It does
not flash loading labels, dim controls or discard drafts, including partially
entered colors. New edits made during an apply remain in the draft.

Tab/arrows select hiding actions; Enter/Space activates them. R refreshes
status, C opens appearance, and Esc closes the panel. Appearance fields
support Tab, arrow adjustment and Home/End range boundaries.

## Safety boundary

Commands use argument arrays, fixed executables and restricted environments.
The watcher emits five fields only: state, address, stable ID, native privacy
and inherited privacy. Socket events are wakeups; titles are neither decoded
nor retained. Stable IDs remain canonical decimal strings across the full
positive uint64 range, without JavaScript number rounding.

Unknown or malformed state cannot grant an action. A failed spoiler renderer
uses a black replacement. Native ABI, release and session admission belong
to the guarded core controller.

**Direct DRM/KMS scanout capture is not protected:** it bypasses the
compositor's sanitized scene. Physical screens and cameras are also outside
this protection. Review the [native capture limits](https://github.com/OBJLAKO/hyprveil)
for the recording path you use.

## Validation

From the repository root:

```sh
python3 -m unittest discover -s tests -v
node plugin/tests/state.test.cjs
python3 plugin/tests/qml-smoke.py --native-config
python3 plugin/tests/qml-smoke.py --status-failure
python3 plugin/tests/qml-smoke.py --configure-failure
python3 plugin/tests/preview-colors.py
```

Python tests use temporary HOME directories and synthetic Unix sockets.
Node tests exercise the state model and execute Lua scenarios for identity,
focus, inherited protection, response validation and idempotence. Local QML
checks use an artificial controller; color checks require Pillow. The CI
workflow runs the unit checks without claiming a compositor integration run.

For a stock KeyboardPanel check, explicitly supply an already-running,
marked isolated runtime created by the native test harness:

```sh
python3 plugin/tests/qml-smoke.py --native-config --lab /tmp/hv-EXPLICIT
```

The independent read-only admission helper checks the marker, owner, process,
sockets and isolation from physical seats. It imports no native source and
does not launch or stop a compositor. Offscreen documentation demos use
`python3 assets/render-previews.py` and synthetic state only. They show the
QML preview, not a native capture recording or personal desktop.
