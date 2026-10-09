# Security

Please report suspected privacy leaks, unsafe command handling, installer
ownership bypasses or window identity races through
[GitHub private vulnerability reporting](https://github.com/OBJLAKO/omarchy-hyprveil/security/advisories/new).
Avoid public issues until the report has been reviewed. Include versions,
reproduction steps and synthetic examples; omit personal screenshots,
window titles and unrelated configuration.

This repository is the Omarchy frontend. It samples no client pixels or
titles and uses a bundled, versioned controller and the public native API.
Hyprpm owns native build/cache/enable state. Explicit first-click terminal setup
can fetch and build the pinned core, write backed-up marked startup/settings,
and selectively load its manager-built artifact. It asks before ordinary setup
and separately before a broader header/manager update. Ordinary enable and
selective activation avoid global compositor synchronization. A separately
authorized `hyprpm update` can rebuild all registered repositories, synchronize
loaded plugins and unload manually loaded modules. Missing build tools or
Hyprpm cache operations may require `sudo`. The exact native pin is recorded in
`native-release.json`; setup refuses other compositor ABIs, unsafe files and
recognized legacy loaders. Existing guarded legacy loading remains an explicit
recovery path for older managed installations. Report
native rendering or capture problems to
[Hyprveil's private reporting page](https://github.com/OBJLAKO/hyprveil/security/advisories/new).

Compositor-based capture is the intended boundary. Direct DRM/KMS scanout
bypasses that boundary and is not protected. Physical displays and cameras
are also outside it. See the [panel guide](docs/GUIDE.md#safety-boundary)
and [native core](https://github.com/OBJLAKO/hyprveil) before choosing a recorder.

The widget and its Python helpers run as ordinary, unsandboxed user code.
The native core is a separate project that can be installed independently or
through confirmed terminal setup. Setup's private ownership record and backups
are under `~/.config/omarchy-hyprveil/`; independent helpers/source live under
`~/.local/share/omarchy-hyprveil/`. Removing the widget intentionally keeps the
native core, startup helper and settings so future-login protection can continue.
Native removal requires a separate deliberate operation after sharing stops.
Repository tests and local
static checks do not constitute marketplace verification or a guarantee of
capture safety. See the [reviewer notes](docs/REVIEW.md) for the command and
installation scope.

There is no promised response deadline or support for old releases. Use the
current repository version with the matching native API and compositor ABI.
