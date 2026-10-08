# Hyprveil panel guide

This Omarchy widget controls [native Hyprveil](https://github.com/OBJLAKO/hyprveil)
through its installed CLI and public Lua API. It requires the 0.4.0 native
API; the core's tested Hyprland version is 0.56.2. The permanent Omarchy
plugin ID is `io.github.objlako.hyprveil`.

## Installation

Follow the [native core installation](https://github.com/OBJLAKO/hyprveil#quick-start)
first and complete its first login to activate the installed core. The panel
requires `~/.local/bin/hyprveil`; it cannot install native code for you.
Then use Omarchy's standard plugin manager:

```sh
omarchy plugin add https://github.com/OBJLAKO/omarchy-hyprveil.git --enable
```

The repository has one root manifest, root QML entry point, README and MIT
license. Omarchy clones and validates the root package directly. No postinstall
script is needed or executed. The UI gives setup guidance when native state
cannot be confirmed. It performs no automatic native installation or loading.
With an installed but unloaded core, the Load button is an explicit user action.

Update a Git-managed installation through Omarchy:

```sh
omarchy plugin update io.github.objlako.hyprveil
```

### Migrate the old widget

If you have the earlier `sky.hyprveil` widget, disable it before adding the
new ID so that only one eye appears:

```sh
omarchy plugin disable sky.hyprveil
omarchy plugin add https://github.com/OBJLAKO/omarchy-hyprveil.git --enable
```

If the older `sky.screen-privacy` bar entry is also enabled, disable that
entry as well. Keep the old directories: existing helper files and keyboard
bindings can remain in use. Standard plugin add does not take over old IDs.

### Optional offline or manual installer

From a checked-out repository, `python3 tools/install.py` is an optional
alternative for a fresh manual installation. For a legacy custom installation,
use the explicit migration:

```sh
python3 tools/install.py --update
```

The installer resolves only the owned `~/.local/bin/hyprveil` executable or
the native installer's exact symlink to
`~/.local/share/hyprveil/controller.py`. It never searches PATH or executes
the controller during installation. It installs root runtime files into
`~/.config/omarchy/plugins/io.github.objlako.hyprveil`.

Existing files and `~/.config/omarchy/shell.json` receive private backups
under `artifacts/shell-install-*` in the checkout. The printed report lists
paths and hashes. Legacy migration requires `--update` before any replacement;
it backs up old runtime files, replaces the named legacy bar entries in place,
preserves unrelated widgets/settings/keybindings and keeps old directories
and helper files. New duplicate owned eye entries are collapsed.

A manual installation is **not Git-managed** and cannot use `omarchy plugin
update`; repeat the manual installer for future updates. Conversely, the
manual installer refuses an existing Git-managed target, preserving that
checkout and directing you to the standard update command.

Links, FIFOs, unsafe ownership/permissions and detected concurrent changes
are refused. A concurrent layout edit remains untouched even if widget files
have already been installed. Neither Hyprland nor native Hyprveil is restarted.
To restore manually, review the reported layout backup against later edits;
previous widget files are beside it. The optional installer gives
`privacy-watch` mode 755; the widget invokes it with fixed `/usr/bin/python3`.

## Language

English is the fallback interface language. A Russian system locale selects
Russian. Override the widget language through Omarchy's existing settings API:

```sh
omarchy bar set io.github.objlako.hyprveil language ru
omarchy bar set io.github.objlako.hyprveil language en
omarchy bar set io.github.objlako.hyprveil language auto
```

`auto` follows the system locale; unsupported values behave like `auto`.
Language changes affect display text only, never native values or commands.

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
| Spoiler / Спойлер | `spoiler` | An opaque procedural mask with satin or Telegram appearance. |
| Omit window / Полностью скрыть | `omit` | Exclude the protected window from compositor capture. |
| Black mask / Обычная маска | `black` | A plain black mask. |
| Restore omission / Вернуть исходное скрытие | `omit` | Return to omission while Hyprveil stays loaded. |

Style changes preserve which windows are private. Your own desktop keeps
its normal window contents. The panel can load the installed native plugin
when it is not loaded; style controls stay disabled until state is confirmed.

## Appearance and native settings

The Appearance / Оформление tab exposes seven fields:

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

**Reload Lua / Перечитать Lua** explicitly reloads configuration and confirms the native
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
node tests/state.test.cjs
python3 tests/qml-smoke.py --native-config --locale en
python3 tests/qml-smoke.py --native-config --locale ru
python3 tests/qml-smoke.py --missing-core --locale en
python3 tests/qml-smoke.py --status-failure
python3 tests/qml-smoke.py --configure-failure
python3 tests/preview-colors.py
```

Python tests use temporary HOME directories and synthetic Unix sockets.
Portable package checks validate the root contract; a local integration test
runs stock Omarchy add/validate/enable with fake git transport and shell IPC.
That stock-source test is skipped when Omarchy is not installed.
Node tests exercise the state model and execute Lua scenarios for identity,
focus, inherited protection, response validation and idempotence. Local QML
checks use an artificial controller; color checks require Pillow. The CI
workflow runs the unit checks without claiming a compositor integration run.

For a stock KeyboardPanel check, explicitly supply an already-running,
marked isolated runtime created by the native test harness:

```sh
python3 tests/qml-smoke.py --native-config --lab /tmp/hv-EXPLICIT
```

The independent read-only admission helper checks the marker, owner, process,
sockets and isolation from physical seats. It imports no native source and
does not launch or stop a compositor. Offscreen documentation demos use
`python3 assets/render-previews.py` and synthetic state only. They show the
QML preview, not a native capture recording or personal desktop.
