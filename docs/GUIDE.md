# Hyprveil panel guide

This Omarchy widget controls [native Hyprveil](https://github.com/OBJLAKO/hyprveil)
through its bundled controller and public Lua API. It requires the 0.5.0 native
API; the core's tested Hyprland version is 0.56.2. The permanent Omarchy
plugin ID is `io.github.objlako.hyprveil`.

## Installation

Install the widget with Omarchy:

```sh
omarchy plugin add https://github.com/OBJLAKO/omarchy-hyprveil.git --enable
```

When native Hyprveil is confirmed unloaded, the first left or middle click
opens `install.sh` in an Omarchy terminal. The Setup native button does the
same. Review the printed changes and confirm there. Unknown native state opens
the panel for diagnostics; it does not authorize setup. Omarchy's initial clone
does not run an install hook. Stop screen sharing before setup or rebuilding.

The terminal installer follows the explicit first-click approach used by
[Omarchy Liquid Glass](https://github.com/fasi96/omarchy-liquid-glass), with
Hyprveil's own native source and selective activation. It requires a running
Hyprland session, the reviewed **0.56.2 ABI**, a readable
`~/.config/hypr/hyprland.lua` and no existing configuration errors.

The [panel setup entry point](https://github.com/OBJLAKO/omarchy-hyprveil#install)
documents this first-click workflow. The independent
[native core](https://github.com/OBJLAKO/hyprveil)
also works without this panel. The panel bundles its API controller and requires
no separate `~/.local/bin/hyprveil` or old installation receipt.

### What setup changes

[`native-release.json`](../native-release.json) pins native version **0.5.0** to
commit `f575f3b757d5b959f0d3e638cf6d98b5a1d0301a`. Setup fetches that exact clean
commit into `~/.local/share/omarchy-hyprveil/native-<commit>` and asks Hyprpm to
build and enable it. Hyprpm's native manifest selects the reviewed source commit
for the supported compositor ABI. The panel does not compile or publish its own
copy directly into the manager cache.

Missing Arch build tools (`base-devel`, `cmake`, `meson`, `cpio`, `pkgconf`, `git`)
may be installed through `sudo pacman -S --needed`. Hyprpm may also request
privilege for headers/cache. If the manager's recorded ABI is stale or absent,
setup separately explains that **`hyprpm update` can rebuild all registered
repositories, synchronize loaded plugins and unload manually loaded modules**,
then asks for consent. `--yes` alone does not grant that broader update. If the
recorded ABI already matches, missing headers are prepared by `hyprpm add`
without forcing a global update.

| Path | Purpose |
| :--- | :--- |
| `~/.config/hypr/hyprland.lua` | A marked `OMARCHY HYPRVEIL SETUP v1` block sources the bootstrap. |
| `~/.config/hypr/hyprveil-hyprpm.lua` | Native plugin permission, managed settings and selective login activation. |
| `~/.config/hypr/hyprveil-settings.lua` | Persistent mode and appearance; an existing valid managed block is preserved. |
| `~/.local/share/omarchy-hyprveil/` | Pinned source and independent setup/controller/uninstall helpers. |
| `~/.config/omarchy-hyprveil/install.json` | Private ownership record for setup's files and native registration. |
| `~/.config/omarchy-hyprveil/backup-*` | Private backups of replaced user files. |

Ordinary setup registers Hyprveil with Hyprpm without letting that command
synchronize the compositor globally. It verifies the requested repository,
revision, enabled state and safe successful binary, reloads Lua, checks
configuration errors and selectively loads `hyprveil.so` from the cache.
It avoids `hyprpm reload`. An explicitly authorized broader manager update
has the additional scope described above. With no registered repositories,
initial header preparation also runs without compositor synchronization and
must pass checks for the reviewed ABI and header version. The login helper
repeats selective activation. Protection is confirmed through the native API before
the UI reports success. Hyprland's plugin permission can require a new login.
If the load command returns successfully but loading remains unconfirmed,
setup exits nonzero with **“setup prepared”** and **“Protection is NOT active
yet”**. It keeps the complete source, helpers, startup/settings and private
receipt (`pending_login: true`). Log out and back in as instructed, then confirm
native state before sharing. A pending request is not active protection.

Existing native Hyprpm installations are reused rather than silently replaced.
Edited setup blocks, unsafe files, multiple repositories providing Hyprveil
and old native loaders are refused. A genuine failed load command or rejected
configuration attempts to restore setup's unchanged files; concurrent edits
are kept. If a concurrent main-config edit may retain the new source block,
rollback keeps the complete helper/settings set and asks you to rerun setup.
A completed native manager build can remain after a later failure. Read the
terminal output before retrying.

### Run setup directly

From the installed widget checkout or a clean checkout of this repository:

```sh
./install.sh
./install.sh --yes
```

`--yes` accepts the ordinary setup changes. Add `--hyprpm-update` only if you
also authorize the broader manager update. `--core-source PATH` uses an owned,
clean local checkout at exactly the pinned native commit; it does not allow
an arbitrary native version. `--plugin-only` requests a native rebuild. It is
allowed only while Hyprveil is unloaded and, for an existing registration,
only when setup's ownership record matches. An externally installed core must
be updated with its original Hyprpm workflow.

### Cold-login migration from the old native installer

Setup refuses `~/.config/hypr/hyprveil.lua` and recognized legacy autoload code
before building. Follow the native
[cold-login migration](https://github.com/OBJLAKO/hyprveil/blob/main/docs/HOST-SETUP.md#migrate-from-the-old-installer)
to remove the old startup loader and end the old compositor session before
using this setup. Do not install a second loader over a running legacy module.
An older managed installation may retain explicit guarded Load/Enable recovery
through its safely owned legacy CLI and receipt; that is a compatibility path.

### Update and remove

Update a Git-managed widget through Omarchy:

```sh
omarchy plugin update io.github.objlako.hyprveil
```

This updates the panel and release pin; it does not replace a loaded native
module. For a setup-owned native rebuild, stop sharing, arrange an unloaded
session without the automatic loader, and run `./install.sh --plugin-only`
from the updated widget checkout. Setup refuses a rebuild if the module is
loaded. Review the native guide before changing the supported compositor ABI.

To remove the widget, use either:

```sh
omarchy plugin remove io.github.objlako.hyprveil
~/.local/share/omarchy-hyprveil/uninstall.sh
```

Both retain native Hyprveil, its selective startup helper, settings, source,
ownership record and backups. Existing and next-login protection can therefore
continue without the widget. Complete native removal is a separate Hyprpm and
Lua configuration operation: stop sharing first and remove only Hyprveil's own
startup block and files after reviewing later edits. There is no `--purge` or
`--native` removal flag.

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
alternative for copying the widget. It is separate from the first-click native
setup. For a legacy custom widget installation,
use the explicit migration:

```sh
python3 tools/install.py --update
```

The installer copies the bundled API controller and root runtime files into
`~/.config/omarchy/plugins/io.github.objlako.hyprveil`. It does not require or
execute a separate CLI, search PATH, build native code or edit Hyprland settings.

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
| Spoiler / Спойлер | `spoiler` | An opaque procedural mask with ten appearance presets. |
| Omit window / Полностью скрыть | `omit` | Exclude the protected window from compositor capture. |
| Black mask / Обычная маска | `black` | A plain black mask. |
| Restore omission / Вернуть исходное скрытие | `omit` | Return to omission while Hyprveil stays loaded. |

Style changes preserve which windows are private. Your own desktop keeps
its normal window contents. Style controls stay disabled until native state is
confirmed. Native builds belong to Hyprpm; the setup helper selectively
activates its registered artifact as described above.

## Appearance and native settings

The Appearance / Оформление tab exposes the pattern controls and an Advanced icon section:

| Field | Range/default |
| :--- | :--- |
| Variant | Prism / Signal / Aurora / Contour / Radar / Matte / 404 / Matrix / Anonymous / Liquid Glass; Prism by default |
| Color | Opaque `#RRGGBB`; white by default |
| Grain | 0–100%; default 50% |
| Speed | 0–200%; default 100%; 0 pauses the pattern; Matte is always still |
| Darkness | 0–100%; default 50% |
| Icon (Advanced) | Eye / Lock / Shield / None; Eye by default |
| Icon size (Advanced) | 40–128 px; default 80 px |
| Icon opacity (Advanced) | 0–100%; default 75%; affects only the icon |

| Preset | Texture |
| :--- | :--- |
| Prism | Animated angular iridescent facets. |
| Signal | Warm phosphor scanlines with a sweeping light band. |
| Aurora | Broad cyan ribbons with a lavender echo. |
| Contour | Organic terracotta topographic cells. |
| Radar | A circular sonar sweep over a green grid. |
| Matte | Still mineral grain; no animation timer. |
| 404 | Giant error digits with occasional glitch slices. |
| Matrix | Cascading green synthetic glyphs. |
| Anonymous | An original illustrated mask with a moving scan glow. |
| Liquid Glass | Floating glass lenses over a synthetic cyan/violet field. |

Old `eye = false` settings still hide the icon. Choosing a shape enables it; choosing None hides it. Old `eye_size` remains the icon size. Native aliases `satin`, `telegram` and `grid` map to Prism, Signal and Radar. `404`, `cmatrix`, `anon`, `liquid-glass` and `liquidglass` are accepted aliases for the new themes.

Preset swatches are actual native GPU captures of synthetic fixtures at fixed reference settings. The larger preview is a procedural illustration of your draft and never samples client pixels. Color and
darkness keep the mask opaque. Apply requires a native acknowledgement and a fresh status check. With no
managed Lua file it changes the current session, and the panel displays a
permanent session-only note. Variant buttons apply immediately while keeping
other parameters. Reset appearance restores defaults and keeps the hiding
mode. When Black or Omit is selected, these parameters take effect after
selecting Spoiler.

The confirmed native mode and appearance determine the controls. Old
installation preferences do not override actual native state.

The first-click installer creates managed persistence. If you installed the
native core independently, you can instead copy its
[managed settings sample](https://github.com/OBJLAKO/hyprveil/blob/main/examples/hyprveil-settings.lua)
to `~/.config/hypr/hyprveil-settings.lua` and integrate the
[Hyprpm startup example](https://github.com/OBJLAKO/hyprveil/blob/main/examples/hyprveil-hyprpm.lua)
into your Hyprland Lua configuration. Preserve any existing files and choose
unused keybindings. The native guide explains the startup permissions.
The runtime style editor changes only the managed settings block. Startup
integration is a separate, explicitly confirmed terminal setup action.

Once the managed literal block exists, panel saves update its settings and
verify the native result after reload. Custom Lua belongs outside that block
and is preserved. Custom code inside it, unsafe file permissions or a later
override can cause a save to be refused; the panel keeps the draft and reports
the failure. A missing managed file permits session-only changes; an unsafe
existing file is refused before changing native state.

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

Runtime privacy commands use argument arrays, fixed executables and restricted
environments. The terminal launcher uses one quoted repository path to run
`install.sh`; the installer invokes its build and activation commands as arrays.
The watcher emits five fields only: state, address, stable ID, native privacy
and inherited privacy. Socket events are wakeups; titles are neither decoded
nor retained. Stable IDs remain canonical decimal strings across the full
positive uint64 range, without JavaScript number rounding.

Unknown or malformed state cannot grant an action. A failed spoiler renderer
uses a black replacement. The native module enforces the reviewed ABI before reading compositor fields;
the controller independently attests process/socket identity. Hyprpm owns the
native build/cache; selective activation checks the manager state and rejects
unsafe cache artifacts. The bundled sources and hashes are recorded in
`native-cli-provenance.json`. Legacy loading keeps its release admission checks.

**Direct DRM/KMS scanout capture is not protected:** it bypasses the
compositor's sanitized scene. Physical screens and cameras are also outside
this protection. Review the [native capture limits](https://github.com/OBJLAKO/hyprveil)
for the recording path you use.

## Validation

From the repository root:

```sh
python3 -m unittest discover -s tests -v
node tests/state.test.cjs
python3 tests/qml-process-failures.py
python3 tests/qml-smoke.py --native-config --locale en
python3 tests/qml-smoke.py --native-config --locale ru
python3 tests/qml-smoke.py --presets --locale ru
python3 tests/qml-smoke.py --missing-core --locale en
python3 tests/qml-smoke.py --status-failure
python3 tests/qml-smoke.py --configure-failure
python3 tests/preview-colors.py
```

Python tests use temporary HOME directories and synthetic Unix sockets.
First-click setup tests use fake Hyprpm/build/activation commands and temporary
configuration/cache fixtures, including ownership and failure paths. They do
not demonstrate a real privileged Hyprpm cache installation or a cold login.
Portable package checks validate the root contract; a local integration test
runs stock Omarchy add/validate/enable with fake git transport and shell IPC.
That stock-source test is skipped when Omarchy is not installed.
Node tests exercise the state model and execute Lua scenarios for identity,
focus, inherited protection, response validation and idempotence. Local QML
checks use an artificial controller; subprocess regression checks cover ignored
SIGTERM, oversized output without line breaks and failed executable startup.
Color checks require Pillow. The CI
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
