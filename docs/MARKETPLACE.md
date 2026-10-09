# Marketplace presentation and updates

Hyprveil brings window capture privacy to the Omarchy bar: a confirmed eye
indicator, one-click privacy and live controls for ten opaque procedural
spoiler presets. Black masking and omission remain one selection away.

| Listing field | Value |
| :--- | :--- |
| Name | Hyprveil |
| Permanent ID | `io.github.objlako.hyprveil` |
| Repository | [OBJLAKO/omarchy-hyprveil](https://github.com/OBJLAKO/omarchy-hyprveil) |
| Category | System |
| Tags | security, bar, hyprland |
| License | MIT |
| Short description | Window capture privacy and spoiler styles, directly from the Omarchy bar. |
| Preview | Root `preview.png` |

## Existing listing

Hyprveil is already published. The initial
[submission #10510](https://github.com/omacom/omarchy-plugin-marketplace/issues/10510)
is closed; do not open another initial submission or edit that historical body
to promote this release. Keep the permanent plugin ID and repository root.

The listing represents the Omarchy controls. The independent
[native Hyprveil](https://github.com/OBJLAKO/hyprveil) repository supplies the
required capture engine and also supports plain Hyprland. Both project links
remain visible in the README. This panel's new first-click installer pins the
native core through `native-release.json`; that native pin is separate from
the exact **panel** commit requested for a marketplace update.

## Installation disclosure

The standard command clones and enables the widget:

```sh
omarchy plugin add https://github.com/OBJLAKO/omarchy-hyprveil.git --enable
```

When native state is confirmed unloaded, a first click opens the installer in
an Omarchy terminal. It shows the changes and asks before building the pinned
native release with Hyprpm. Unknown native state opens diagnostics instead.
No post-install hook runs during the clone, and no separate CLI is required.

Setup may install missing Arch build tools with `sudo pacman` and may require
privilege for Hyprpm headers/cache. A broader `hyprpm update` requires separate
consent. Setup adds backed-up, marked Lua startup and managed persistent settings,
then selectively activates only Hyprveil. The supported native ABI is currently
Hyprland 0.56.2. Removing the widget keeps the native core, startup helper,
settings and source. See [the setup guide](GUIDE.md#installation).

The existing **manual-setup** override stays in place: this release still
requires an explicit terminal setup step. Its source-build and configuration
behavior should be disclosed as `remote-build` and `installer` capabilities.
Do not check the optional assertion that installation requires no manual setup,
or request removal of the override as part of this update. A later change to
installation presentation requires the marketplace's separate guarded review.

## Request a newer snapshot

Use the official
[Plugin verification form](https://github.com/omacom/omarchy-plugin-marketplace/issues/new?template=verify-plugin.yml)
with the title **[Verify]: Hyprveil** and action
**Verify and publish a newer upstream commit**. Supply:

- Plugin ID `io.github.objlako.hyprveil`.
- Repository URL `https://github.com/OBJLAKO/omarchy-hyprveil`.
- The full 40-character SHA of the published, current **panel repository HEAD**.
- The required exact-commit verification acknowledgment.

[submission-draft.md](submission-draft.md) is a template with a deliberately
unresolved target-commit placeholder. It is not a posted request or a claim of
verification. Replace the placeholder only after publishing and checking the
final commit. Do not use the native core pin as the panel target commit.

The current [submission guide](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/SUBMISSION.md)
and [verification process](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/VERIFICATION.md)
were checked on 2026-10-09. Compatibility validation and the static baseline
inspect the exact target without executing community code. A maintainer must
review the current reports and approve update promotion. The existing snapshot
remains authoritative while the update is pending. Successful promotion replaces
it atomically and retains its history. Verification describes only that exact
snapshot and is not a security audit or safety guarantee. Stock Omarchy install
and update commands still follow mutable upstream HEAD.

## Preview and scope

`preview.png` is a minimal explanatory illustration: a private window stays
visible locally and gets an opaque mask in the screen share. It contains no
desktop capture. Actual native synthetic recordings and offscreen QML panel
screenshots appear separately in the README. Their distinct provenance is
recorded in [assets/provenance.json](../assets/provenance.json),
[assets/cover-provenance.json](../assets/cover-provenance.json) and
[assets/native-capture-provenance.json](../assets/native-capture-provenance.json).

Describe the promise as **compositor capture privacy**. Direct DRM/KMS capture
bypasses the protected scene. Protection begins only after native loading is
confirmed. The root preview is a static image; animated native examples belong
in the README. Marketplace presentation does not expand the capture boundary.
