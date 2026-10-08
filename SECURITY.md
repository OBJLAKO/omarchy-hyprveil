# Security

Please report suspected privacy leaks, unsafe command handling, installer
ownership bypasses or window identity races through
[GitHub private vulnerability reporting](https://github.com/OBJLAKO/omarchy-hyprveil/security/advisories/new).
Avoid public issues until the report has been reviewed. Include versions,
reproduction steps and synthetic examples; omit personal screenshots,
window titles and unrelated configuration.

This repository is the Omarchy frontend. It samples no client pixels or
titles and uses the installed Hyprveil CLI and public native API. Report
native rendering or capture problems to
[Hyprveil's private reporting page](https://github.com/OBJLAKO/hyprveil/security/advisories/new).

Compositor-based capture is the intended boundary. Direct DRM/KMS scanout
bypasses that boundary and is not protected. Physical displays and cameras
are also outside it. See the [panel guide](plugin/README.md#safety-boundary)
and [native core](https://github.com/OBJLAKO/hyprveil) before choosing a recorder.

There is no promised response deadline or support for old releases. Use the
current repository version with the matching native API and compositor ABI.
