# Notification privacy: supported behavior and proposed integration

This is a feasibility/design note, **not a claim that per-card notification
styles or notification controls have shipped**. No notification settings are
changed by the panel update that carries this note.

## What the native core already supports

Native Hyprveil 0.6.0 omits a layer marked `no_screen_share` when constructing
its protected capture scene (`src/main.cpp`, `layerHook`). That policy is
independent of private-window appearance. Consequently, notification content
can disappear from a supported capture while private windows keep 404, an
image or a custom shader. The local desktop remains visible. Ordinary private
layers are omitted; they do not inherit window replacement rectangles.

The inspected Omarchy **4.0.4** service `omarchy.notifications` **1.0.0** uses
the layer-shell namespace `omarchy-notifications`. Its Quickshell service owns
the desktop notification D-Bus name. Its `Service.qml` creates one transparent,
**full-screen** `PanelWindow` per output, with several `NotificationCard`
children stacked at the top right. An input mask covers the toast column.
The layer deliberately remains full-screen to avoid stale-buffer scaling when
notifications change size. A layer's input mask is not a reliable description
of every card's rendered pixels, rounding, image or shadow.

Omitting this transparent layer removes its notifications and exposes the
sanitized scene behind it. It does **not** black out the monitor. Conversely,
drawing an opaque replacement using that layer's full geometry would black out
the monitor. That must never be used as a notification-style fallback. The
current omission behavior must remain the safe default for unintegrated layers.

## Proposed user controls

Expose separate **Windows** and **Notifications** sections in the Omarchy panel,
backed by separate typed settings/status in the native Hyprpm core. Keep window
settings independent. The notification section should initially offer normal
capture or omission for an exact configured notification namespace. Later,
integrated per-card surfaces can offer Color, Spoiler/404, Image with its fit
mode, custom procedural GLSL and icon settings, with their own profile.

In a standalone Hyprpm installation, the same profile must be configurable
through Lua without the Omarchy widget. Existing `no_screen_share` layer rules
must retain their current omission semantics. Never target every Quickshell
surface by process ID: the bar, launcher, menus and notification service share
a process. Namespace matching must be exact and opt-in for unfamiliar managers.

## Geometry needed for individual replacement cards

The compositor sees Wayland surfaces, not QML `NotificationCard` objects or
notification sender names. It cannot infer individual card boundaries safely
from a full-screen transparent layer. There are two possible integrations:

1. **Prefer separate bounded layer surfaces for each toast**, retaining the
   stable-buffer behavior in each card's envelope. Each has a known small
   geometry and an explicit privacy/style capability. Native code can omit its
   original surface and draw a synthetic replacement at its real stack position.
2. A cooperative, versioned geometry protocol from a trusted notification
   manager can publish card bounds tied to a particular surface, output and
   committed buffer generation. Geometry must be atomic with content updates;
   an ordinary periodic JSON/IPC list can race a new toast and leak its first
   frame. This approach requires more protocol and lifecycle work than option 1.

Do not derive card bounds by sampling private pixels, applying a desktop-wide
shader, guessing a fixed top-right rectangle or using an input region as a
pixel mask. If the integration, generation, geometry or asset fails, omit the
notification layer/card. Do not cover the monitor with a synthetic fill. Card
shader errors may fall back to the selected opaque color only when the card's
bounded geometry is established.

Per-application notification filtering also requires manager cooperation:
several senders share the same Wayland surface. An app-name hint is a user
filter, not authenticated sender identity. The notification center/history is
a separate surface/interaction and must have an explicit policy of its own.

## Required validation before shipping

Use synthetic notifications in an isolated compositor. Check zero private
pixels in supported monitor, region and window exports; unaffected pixels
outside each card; simultaneous 404 windows; multiple toasts and outputs;
scale/zoom, rounding and shadows; arrival, replacement, expiry and close;
fullscreen stacking; late geometry; manager restart/disconnect; and invalid
images/shaders. An unknown manager must remain on omission and report that
per-card styling is unavailable. Do not claim compatibility with every manager
or capture backend before those tests pass.
