import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Io
import qs.Ui as Ui
import "I18n.js" as I18n

// Qt's automatic canPaste update can synchronously fetch foreign clipboard
// data even when the field is unfocused. Keep the underlying editor read-only
// for its entire lifetime; handle edits here and paste only through a bounded
// child. Disabling native paste shortcuts alone does not prevent that read.
Ui.TextField {
    id: root
    readOnly: true
    cursorVisible: activeFocus
    selectByMouse: true
    property bool pasteFailed: false
    property bool pastePending: false
    readonly property bool pasteBusy: pastePending || pasteReader.running
    property int editGeneration: 0
    property int pasteGeneration: -1
    property int pasteStart: 0
    property int pasteEnd: 0
    property var undoStates: []
    property var redoStates: []
    property bool internalEdit: false
    property string language: I18n.language(Qt.locale().name)
    readonly property var pasteEnvironment: {
        const env = {PATH: "/usr/bin:/bin", LANG: "C.UTF-8"}
        for (const name of ["HOME", "XDG_RUNTIME_DIR", "WAYLAND_DISPLAY"]) {
            const value = Quickshell.env(name)
            if (value !== undefined && value !== null && String(value) !== "") env[name] = String(value)
        }
        return env
    }
    onTextChanged: {
        editGeneration++
        if (!internalEdit) { undoStates = []; redoStates = [] }
    }
    Controls.ToolTip.visible: pasteFailed && activeFocus
    Controls.ToolTip.text: I18n.text("paste_refused", language)
    Controls.ToolTip.timeout: 4000
    Connections {
        target: root
        function onActiveFocusChanged() { root.editGeneration++ }
        function onEnabledChanged() { root.editGeneration++ }
    }

    function snapshot() { return {text: text, cursor: cursorPosition} }
    function remember() {
        undoStates = undoStates.slice(-15).concat([snapshot()])
        redoStates = []
    }
    function setEdited(value, cursor) {
        internalEdit = true
        try { text = value; cursorPosition = cursor }
        finally { internalEdit = false }
        pasteFailed = false
        textEdited()
    }
    function replaceRange(start, end, value) {
        if (text.length - (end - start) + value.length > maximumLength) {
            pasteFailed = true
            return
        }
        remember()
        setEdited(text.slice(0, start) + value + text.slice(end), start + value.length)
    }
    function insertText(value) { replaceRange(selectionStart, selectionEnd, value) }
    function undoEdit(redo) {
        const source = redo ? redoStates : undoStates
        if (!source.length) return
        const state = source[source.length - 1]
        if (redo) {
            undoStates = undoStates.slice(-15).concat([snapshot()])
            redoStates = source.slice(0, -1)
        } else {
            redoStates = redoStates.slice(-15).concat([snapshot()])
            undoStates = source.slice(0, -1)
        }
        setEdited(state.text, Math.min(state.cursor, state.text.length))
    }
    function requestPaste() {
        if (!enabled || !activeFocus || pasteBusy) return
        pasteGeneration = editGeneration
        pasteStart = selectionStart
        pasteEnd = selectionEnd
        pasteFailed = false
        pastePending = true
        pasteReader.running = true
    }
    function receivePaste(raw) {
        // A delayed result must not replace newer typing, an external state
        // refresh, a moved selection or a field that has lost focus.
        if (!enabled || !activeFocus || editGeneration !== pasteGeneration ||
                selectionStart !== pasteStart || selectionEnd !== pasteEnd) return
        try {
            const result = JSON.parse(raw)
            if (result.ok !== true || typeof result.text !== "string" || result.text.length > maximumLength) {
                pasteFailed = true
                return
            }
            insertText(result.text)
        } catch (_) { pasteFailed = true }
    }
    function handleKey(event) {
        const control = !!(event.modifiers & (Qt.ControlModifier | Qt.MetaModifier))
        const shift = !!(event.modifiers & Qt.ShiftModifier)
        const alt = !!(event.modifiers & Qt.AltModifier)
        if ((control && !alt && event.key === Qt.Key_V) || (shift && event.key === Qt.Key_Insert)) {
            requestPaste(); event.accepted = true
        } else if (control && !alt && event.key === Qt.Key_X) {
            copy(); if (selectionStart !== selectionEnd) insertText("")
            event.accepted = true
        } else if (control && !alt && (event.key === Qt.Key_Z || event.key === Qt.Key_Y)) {
            undoEdit(event.key === Qt.Key_Y || shift); event.accepted = true
        } else if (event.key === Qt.Key_Backspace || event.key === Qt.Key_Delete) {
            let start = selectionStart; let end = selectionEnd
            if (start === end) {
                if (event.key === Qt.Key_Backspace && start > 0) {
                    start = control ? text.slice(0, start).replace(/\s*\S+\s*$/, "").length : start - 1
                    if (start > 0 && text.charCodeAt(start) >= 0xdc00 && text.charCodeAt(start) <= 0xdfff) start--
                } else if (event.key === Qt.Key_Delete && end < text.length) {
                    end = control ? end + (text.slice(end).match(/^\s*\S+\s*/) || [text.slice(end)])[0].length : end + 1
                    if (end < text.length && text.charCodeAt(end) >= 0xdc00 && text.charCodeAt(end) <= 0xdfff) end++
                }
            }
            if (start !== end) replaceRange(start, end, "")
            event.accepted = true
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            accepted(); editingFinished(); event.accepted = true
        } else if ((!control || alt) && event.text.length && !/[\x00-\x1f\x7f-\x9f]/.test(event.text)) {
            insertText(event.text); event.accepted = true
        }
    }
    Keys.priority: Keys.BeforeItem
    Keys.onPressed: function(event) { handleKey(event) }
    Keys.onShortcutOverride: function(event) {
        if (((event.modifiers & (Qt.ControlModifier | Qt.MetaModifier)) &&
                [Qt.Key_V, Qt.Key_X, Qt.Key_Z, Qt.Key_Y].indexOf(event.key) >= 0) ||
                ((event.modifiers & Qt.ShiftModifier) && event.key === Qt.Key_Insert)) event.accepted = true
    }
    Process {
        id: pasteReader
        command: ["/usr/bin/python3", "-I", decodeURIComponent(String(Qt.resolvedUrl("clipboard-read")).replace(/^file:\/\//, ""))]
        running: false
        clearEnvironment: true
        environment: root.pasteEnvironment
        stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.receivePaste(text) }
        onExited: function(exitCode, exitStatus) {
            root.pastePending = false
            if (exitCode !== 0) root.pasteFailed = true
        }
    }
    Timer {
        interval: 1500
        running: root.pastePending
        onTriggered: { root.pasteFailed = true; root.pastePending = false; pasteReader.running = false }
    }
}
