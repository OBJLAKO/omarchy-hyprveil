# Marketplace presentation

Hyprveil brings window capture privacy to the Omarchy bar: a confirmed eye
indicator, one-click privacy and live controls for opaque Satin or Telegram
spoilers. Black masking and omission remain one selection away.

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

The listing represents the Omarchy controls. The independent
[native Hyprveil](https://github.com/OBJLAKO/hyprveil) repository supplies the
required capture engine and supports plain Hyprland too. Keep both links
visible in the README, with native setup preceding the widget command.

## What the marketplace supports

New submissions use a root `manifest.json`, README and license. The marketplace
reads one root PNG, JPEG, WebP or AVIF preview and produces static card/detail
images. The README carries the additional screenshots and animated QML demo.
These formats and the submission template come from the
[official submission guide](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/SUBMISSION.md).

For root plugins, the standard install command clones and enables the widget;
it does not install a native companion. The catalog also supports a maintainer
`manual-setup` designation, which displays prerequisite guidance instead of a
one-step install command. Request that designation for Hyprveil. See the
[catalog installation logic](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/scripts/build-catalog.mjs)
and [approval workflow](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/.github/workflows/approve-submission.yml).

Suggested setup note:

> Install native Hyprveil 0.4.0 first, using the pinned source instructions in
> the README. It requires the exact supported Hyprland ABI (tested on 0.56.2).
> A first native installation activates at the next login. Then add this
> Omarchy widget using the standard plugin command.

## Preview and scope

`preview.png` combines the real English QML appearance panel with an actual
native before/after capture of synthetic notes. Each material is labeled.
The assets contain no personal desktop content. Native capture and QML preview
are distinct; [provenance](../assets/provenance.json) records their sources.

Describe the promise as **compositor capture privacy**. Direct DRM/KMS capture
bypasses the protected compositor scene. Put that boundary beside the supported
ABI in the README, without implying that the widget installs native protection
by itself.

## Owner review before submission

[submission-draft.md](submission-draft.md) preserves the official issue fields.
Its five checkboxes intentionally remain unchecked. The owner must confirm
each statement, review the complete body and approve posting it. Proposed issue
title: **[Plugin]: Hyprveil**. No issue has been created by preparing this draft.

The intended ID was absent from the primary registry and catalog when checked
on 2026-10-08; recheck before submitting because IDs are permanent, including
retired IDs. Marketplace publication and verification require maintainer review
of the exact commit. This repository makes no marketplace verification claim.
See the [official verification process](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/VERIFICATION.md).
