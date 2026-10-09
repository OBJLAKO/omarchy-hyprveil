# Reviewer notes

This repository provides the Omarchy bar widget and style editor. Its permanent
plugin ID is `io.github.objlako.hyprveil`; the repository root contains the single
manifest and its `BarWidget.qml` entry point. The separate
[Hyprveil core](https://github.com/OBJLAKO/hyprveil) owns capture rendering,
native release admission and the public configuration/API contract. This panel
provides explicit terminal setup and selective activation of the core's
Hyprpm-built artifact; it contains no second capture implementation.

## Dependencies and installation scope

The widget requires Omarchy's plugin framework, Quickshell, Python 3,
`/usr/bin/hyprctl`, Hyprpm and native Hyprveil 0.5.0. The core enforces its
reviewed compositor ABI before accessing internal objects. This repository
bundles its receipt-free API controller and service module;
`native-cli-provenance.json` records source/output hashes. The only source
adaptation is the sibling service import name.

Standard `omarchy plugin add` reads the root manifest and clones the repository.
It does not run an install hook, build native code or grant native plugin
permission. A click with confirmed unloaded native state opens `install.sh`
in an Omarchy terminal. Unknown state opens diagnostics instead. The terminal
shows the changes and asks before setup. No separate CLI or legacy native
receipt is required. The existing marketplace **manual-setup** override remains
appropriate while this explicit terminal setup is required; this update does
not request its removal.

`tools/setup.py` fetches the exact native commit in `native-release.json`
(`f575f3b757d5b959f0d3e638cf6d98b5a1d0301a`, version 0.5.0), verifies a clean
checkout and delegates build/cache registration to Hyprpm. Missing Arch build
tools can require `sudo pacman`; Hyprpm headers/cache can also require privilege.
Header updates get separate consent because `hyprpm update` may rebuild other
repositories. `--yes` alone does not authorize that broader update.

Confirmed setup writes a marked Lua source block, a selective login helper and
managed persistent settings. It keeps private backups and an ownership record
under `~/.config/omarchy-hyprveil/`, with independent helpers/source under
`~/.local/share/omarchy-hyprveil/`. Existing managed settings are preserved;
legacy autoload, ambiguous providers, edited owned blocks and unsafe paths are
refused. Rollback restores only unchanged files and preserves concurrent edits;
a completed manager build can remain after a later failure.
If a successful load command leaves native loading unconfirmed, setup instead
preserves the complete files and receipt with `pending_login: true`, exits
nonzero and explicitly reports that protection is not active until confirmed
after login. A failed load command or rejected configuration follows rollback.

Activation reads Hyprpm state and checks its root/user-owned, nonwritable,
single-link cache artifact before loading only `hyprveil.so`. Setup avoids a
global `hyprpm reload`. Rebuilds require an unloaded module and matching setup
ownership for an existing registration. An external registration is reused
without replacement and retains its original update workflow. The conservative
uninstaller removes only the Omarchy widget: native source, registration,
startup helper, settings, ownership record and backups remain.

`tools/install.py` is a separate optional per-user widget-copy installer. It
copies a fixed list of runtime files into the plugin directory and adds or
explicitly migrates the widget entry in `~/.config/omarchy/shell.json`.
Replacement and legacy migration require `--update`. It preserves unrelated
layout, settings and keybindings and creates private rollback copies under
the checkout's ignored `artifacts/` directory. It refuses Git-managed targets
and directs those installations to the stock Omarchy updater. It does not
execute the bundled controller, edit Hyprland configuration, restart Hyprland
or request privilege. Concurrent layout edits are kept; widget files may
already have been copied. Legacy directories remain for existing bindings.
Neither installer runs on import or from the root manifest. Installing this
frontend is not a substitute for reviewing or verifying the separate core.

## Runtime command surface

Privacy/control operations use fixed argument arrays. The first-click terminal
launcher uses a shell-quoted repository path for `cd <path> && ./install.sh`;
the setup helper then uses argument arrays and a restricted environment:

| Component | Command and purpose |
| --- | --- |
| Privacy watcher | `/usr/bin/python3` runs packaged `privacy-watch`; fixed `hyprctl` arguments read native active-window privacy. |
| Window action | `/usr/bin/hyprctl -i <instance> eval <generated Lua>` calls the public native setter for the pinned address and stable ID. |
| Panel | `/usr/bin/python3 <packaged panel-controller>` reads status and executes explicitly selected native API actions. |
| Explicit setup | `omarchy-launch-floating-terminal-with-presentation` opens the installer; confirmed setup uses `git`, `pacman`/`sudo`, `hyprpm` and `hyprctl`. |
| Legacy recovery | Only an explicitly selected Load/Enable action may execute a safely owned legacy CLI after validating its private receipt. |

Child environments are restricted. QML reads raw output chunks with a 32 KiB
status cap and 2 KiB privacy cap; ignored output has no line buffer. Timeout
handlers send SIGKILL and retain process ownership until actual exit. Failed
executable startup immediately clears the pending operation. Generated Lua
accepts validated identity strings and an explicit desired state. The native
API verifies focus, address and stable identity atomically and refuses to reveal
inherited protection. Unknown state disables privacy-changing actions.
Confirmation comes from fresh native state rather than an optimistic UI result.

The watcher binds to one owned runtime and compositor instance and validates its
socket/process identity. Socket events serve as bounded wakeups; their titles
are not decoded or logged. It emits only state, address, decimal stable ID,
native privacy and inherited privacy. The frontend reads no client pixels,
records no screenshots and sends no telemetry. The larger appearance preview
is procedural; preset swatches are native captures of synthetic lab fixtures,
with packaged provenance.

Hyprpm owns native build/cache/enable state; the setup helper activates its
registered artifact selectively. Explicit legacy recovery can load an older
managed release through its guarded CLI. Native API actions can reload Lua.
Saving appearance or mode delegates to the core controller's managed settings
block. These are documented user actions, not install hooks. Without managed
Lua, changes affect only the current session and the panel displays that limit.
A managed file enables guarded persistence; unsafe or custom persistence is
refused before native mutation. All components are ordinary unsandboxed user
processes; fixed arguments and validation do not provide an OS sandbox.

## Review evidence and limitations

Unit checks cover widget installation and first-click setup preservation,
refusals and failure recovery; watcher admission and bounded output; identity
checks; configuration state; and executable Lua fixtures. Synthetic QML checks
exercise panel behavior, ten presets, four icon choices, failed startup,
SIGTERM-resistant children and oversized output without delimiters. They do
not demonstrate native renderer safety on another compositor build.

Setup checks use temporary homes and synthetic manager/activation commands;
they do not claim a live privileged Hyprpm cache installation or a cold-login
validation. Native GPU recordings are isolated synthetic compositor captures;
the main cover is an explanatory illustration and panel screenshots are Qt
offscreen renders. Their provenance is recorded separately. Capture limits
are documented in the [panel guide](GUIDE.md#safety-boundary) and core repository;
direct DRM/KMS scanout and physical displays are outside the protected boundary.

Local preflight uses the marketplace's static scanner and compatibility checks;
it does not execute community plugin code. Its results are **not a marketplace
verification, approval, security audit or safety guarantee**. Pinned source-build
setup and optional installers are expected to expose `remote-build` and
`installer` review capabilities. Those capabilities must remain visible to
maintainers rather than be suppressed.

The marketplace [submission guide](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/SUBMISSION.md)
and [verification process](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/VERIFICATION.md)
were checked on 2026-10-09. Hyprveil is already listed; a newer release uses
**Verify and publish a newer upstream commit** for the exact final panel HEAD,
with fresh maintainer review. The existing snapshot remains in place while
that request is pending. Stock Omarchy install/update commands follow mutable
upstream HEAD; they are not bound to a marketplace verification snapshot.
