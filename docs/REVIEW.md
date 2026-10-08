# Reviewer notes

This repository provides the Omarchy bar widget and style editor. Its permanent
plugin ID is `io.github.objlako.hyprveil`; the repository root contains the single
manifest and its `BarWidget.qml` entry point. The separate
[Hyprveil core](https://github.com/OBJLAKO/hyprveil) owns compositor loading,
capture rendering, native release admission and persisted Hyprland settings.

## Dependencies and installation scope

The widget requires Omarchy's plugin framework, Quickshell, Python 3,
`/usr/bin/hyprctl`, and native Hyprveil's 0.4.0 API and installed CLI. Native
Hyprveil must be built for its supported exact compositor ABI; a matching
version number alone is insufficient. The root README pins the reviewed native
source used in its installation instructions. This is an external dependency,
not native code bundled inside this plugin.

Standard `omarchy plugin add` reads the root manifest and copies the repository.
It does not run `tools/install.py`, build native code, install the native CLI or
grant the native plugin permission. The native prerequisite must be installed
separately before the widget can function. A marketplace submission should
therefore disclose **manual setup** to maintainers.

`tools/install.py` is an optional per-user installer for an existing native
installation. It copies a fixed list of runtime files into the plugin directory
and adds or explicitly migrates the widget entry in `~/.config/omarchy/shell.json`.
Replacement and legacy migration require `--update`. It preserves unrelated
layout, settings and keybindings and creates private rollback copies under
the checkout's ignored `artifacts/` directory. It refuses Git-managed targets
and directs those installations to the stock Omarchy updater. It does not
execute the native controller, edit Hyprland configuration, restart Hyprland
or request privilege. Detected concurrent layout changes are left untouched;
widget files may already have been copied. Legacy directories are retained
for existing bindings and are not silently deleted.

The installer is not invoked on import or by the root manifest. Installing this
frontend is not a substitute for installing, reviewing or verifying the core.

## Runtime command surface

QML launches fixed argument arrays rather than a shell command string:

| Component | Command and purpose |
| --- | --- |
| Privacy watcher | `/usr/bin/python3` runs the packaged `privacy-watch`; fixed `hyprctl` arguments read native active-window privacy. |
| Window action | `/usr/bin/hyprctl -i <instance> eval <generated Lua>` calls the public native setter for the pinned address and stable ID. |
| Panel | `~/.local/bin/hyprveil` reads status and executes an explicitly chosen mode, appearance, load or reload action. |

Child environments are restricted; timeouts and output sizes are bounded. The
generated Lua accepts validated identity strings and an explicit desired state.
The native API verifies focus, address and stable identity atomically and refuses
to reveal inherited protection. Unknown state disables state-changing actions.
Confirmation comes from fresh native state rather than an optimistic UI result.

The watcher binds to one owned runtime and compositor instance and validates its
socket/process identity. Socket events serve as bounded wakeups; their titles
are not decoded or logged. It emits only state, address, decimal stable ID,
native privacy and inherited privacy. The frontend does not read client pixels,
record screenshots or send telemetry. Appearance previews are procedural.

Explicit panel actions can load the separately installed native plugin or reload
Hyprland Lua. Saving appearance or a mode delegates to the core controller's
managed settings block. These are documented user actions, not install hooks.
All components remain ordinary unsandboxed user processes; fixed arguments and
validation do not provide an operating-system sandbox.

## Review evidence and limitations

Unit checks cover installer preservation/refusals, watcher admission and bounded
output, identity checks, configuration state and executable Lua action fixtures.
Synthetic QML checks exercise panel behavior and failed-controller paths. Those
checks do not demonstrate native renderer safety on another compositor build.
Capture limits are documented in the [panel guide](GUIDE.md#safety-boundary) and
the core repository; direct DRM/KMS scanout and physical displays are outside
the compositor capture boundary.

Local preflight uses the marketplace's static scanner and compatibility checks;
it does not execute community plugin code. Its results are **not a marketplace
verification, approval, security audit or safety guarantee**. The source-build
instructions and optional installer are expected to expose `remote-build` and
`installer` review capabilities. Their presence should remain visible to the
maintainer rather than be suppressed.

The checked policy is marketplace commit
[`92758f8aa9a7a466433a1877cba3e60f66679267`](https://github.com/omacom/omarchy-plugin-marketplace/tree/92758f8aa9a7a466433a1877cba3e60f66679267).
See its [submission guide](https://github.com/omacom/omarchy-plugin-marketplace/blob/92758f8aa9a7a466433a1877cba3e60f66679267/SUBMISSION.md),
[security baseline](https://github.com/omacom/omarchy-plugin-marketplace/blob/92758f8aa9a7a466433a1877cba3e60f66679267/SECURITY.md)
and [verification limits](https://github.com/omacom/omarchy-plugin-marketplace/blob/92758f8aa9a7a466433a1877cba3e60f66679267/VERIFICATION.md).
The official submission workflow requires owner confirmation and a fresh
exact-commit maintainer decision. Stock Omarchy install/update commands follow
mutable upstream HEAD; they are not bound to a marketplace verification snapshot.
