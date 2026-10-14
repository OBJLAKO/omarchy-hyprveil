# Clipboard isolation in panel 1.7.1

Marketplace update [#11068](https://github.com/omacom/omarchy-plugin-marketplace/issues/11068#issuecomment-6111779034)
reported an unbounded clipboard read through editable native Qt fields. Field
length validation runs after a native clipboard read and cannot bound that read.
Disabling Ctrl+V alone also leaves automatic `canPaste` updates exposed.

All five editors (two colors, image, icon and shader paths) now use
`SafeTextField.qml`. The underlying Qt field stays `readOnly: true` throughout
its lifetime, including focus, selection, typing and paste. Keyboard edits use
bounded string updates; the component never invokes native `paste()` or reads
`canPaste` to decide whether to enable a paste action. Native middle-click
selection paste remains disabled. Selection, copy, navigation, normal keyboard
text, deletion and bounded undo/redo remain available.

Ctrl+V and Shift+Insert explicitly start the bundled `clipboard-read` helper
using isolated Python, a fixed argv and an allowlisted environment. It invokes
only `/usr/bin/wl-paste --no-newline --type text`. Clipboard changes never start
this helper. It accepts at most **16 KiB of UTF-8**, requires EOF and successful
process exit within one **750 ms total deadline**, and rejects invalid UTF-8,
control characters, partial and oversized input. The reader has a 128 MiB
address-space limit, a CPU limit and parent-death protection. Cleanup kills its
process group. The UI adds a 1.5-second outer deadline and ignores results after
typing, external refresh, moved selection, focus handoff or disablement. No
clipboard contents are logged. A failed paste leaves the field unchanged and
shows a translated hint; the field's existing 7/4096-character limit and value
validation still apply.

The guarded keyboard path does not provide native IME preedit/composition or
native context-menu paste. Unicode keyboard events and bounded Unicode paste
are supported. For an IME-generated path, compose it elsewhere and use Ctrl+V.
An unavailable `wl-paste` produces a failed paste, not a native fallback. No
package installation is performed by paste.

## Verification

`tests/clipboard-qt.cpp` uses an offscreen synthetic `QMimeData` provider and a
real Qt Quick Controls field. On local Qt **6.11.2**, the unfocused writable
positive control performed two provider probes including one payload read;
the read-only cases performed **zero** probes. This does not claim execution of
Qt 6.12 or an actual streaming Wayland exploit. The reviewed Qt 6.12
`q_canPasteChanged`/`canPaste` implementation also short-circuits when read-only.

Twelve Python tests cover finite Unicode, exact limit, infinite/slow/stalled
streams, EOF without exit, invalid text, failed partial input, child limits,
environment isolation and owner death. `tests/qml-safe-input.py` runs the actual
component with an isolated delayed synthetic provider and covers keyboard
editing, Unicode deletion, undo/redo, explicit paste and stale-result rejection.
It never accesses the desktop clipboard. The existing 26 QML autosave scenarios
remain applicable to the guarded fields. CI also compiles and runs the native
Qt positive/negative control on its packaged Qt version.

This change protects Hyprveil's own editors. It does not modify other Omarchy
widgets or claim protection for arbitrary editable controls in the shared shell.
Native Hyprveil remains pinned to the same 0.6.0 source and ABI; installer and
package-manager capabilities and the manual-setup override remain unchanged.
