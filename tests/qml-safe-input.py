#!/usr/bin/python3
"""Actual offscreen guarded editor and asynchronous paste integration."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
QML = r'''import QtQuick
import QtTest
import Quickshell
import "./plugin" as Plugin
ShellRoot {
    property int stage: 0
    property int ticks: 0
    property int edits: 0
    property int checks: 0
    function expect(condition, reason) { checks++; if (!condition) throw new Error(reason) }
    function key(value, code, modifiers) { field.handleKey({text:value, key:code || 0, modifiers:modifiers || 0, accepted:false}) }
    Window {
        visible: true; width: 500; height: 200
        Plugin.SafeTextField { id: field; width: 460; maximumLength: 64
            onTextEdited: edits++ }
        TestCase { id: keyDriver; name: "GuardedEditorKeys"; when: false }
        Item { id: other; focus: false }
    }
    Timer {
        running: true; repeat: true; interval: 20
        onTriggered: {
            ticks++
            try {
                if (stage === 0) {
                    field.forceActiveFocus()
                    if (!field.activeFocus) return
                    expect(field.readOnly && !field.canPaste, "underlying field can read native clipboard")
                    keyDriver.keyClick(Qt.Key_A)
                    expect(field.text === "a", "actual Qt key dispatch did not edit")
                    keyDriver.keyClick(Qt.Key_Backspace)
                    expect(field.text === "", "actual Qt key dispatch did not delete")
                    key("/tmp/Привет🙂.png")
                    expect(field.text === "/tmp/Привет🙂.png" && edits === 3, "Unicode typing failed")
                    field.select(5, 11); key("новый")
                    expect(field.text === "/tmp/новый🙂.png", "selection replacement failed")
                    field.cursorPosition = 12; key("", Qt.Key_Backspace)
                    expect(field.text === "/tmp/новый.png", "surrogate deletion failed")
                    key("", Qt.Key_Z, Qt.ControlModifier)
                    expect(field.text === "/tmp/новый🙂.png", "undo failed")
                    key("", Qt.Key_Y, Qt.ControlModifier)
                    expect(field.text === "/tmp/новый.png", "redo failed")
                    field.selectAll(); key("a".repeat(65))
                    expect(field.text === "/tmp/новый.png" && field.pasteFailed, "over-limit edit truncated input")
                    keyDriver.keyClick(Qt.Key_A, Qt.ControlModifier)
                    keyDriver.keyClick(Qt.Key_V, Qt.ControlModifier)
                    expect(field.pasteBusy, "paste shortcut did not start child")
                    stage = 1
                } else if (stage === 1 && !field.pasteBusy) {
                    expect(field.text === "/tmp/новая иконка.png" && !field.pasteFailed, "explicit async paste failed")
                    field.selectAll(); key("", Qt.Key_V, Qt.ControlModifier)
                    key("newer")
                    stage = 2
                } else if (stage === 2 && !field.pasteBusy) {
                    expect(field.text === "newer", "delayed paste overwrote newer typing")
                    field.selectAll(); key("", Qt.Key_Insert, Qt.ShiftModifier)
                    other.forceActiveFocus(); field.forceActiveFocus()
                    stage = 3
                } else if (stage === 3 && !field.pasteBusy) {
                    expect(field.text === "newer", "paste survived focus handoff")
                    field.selectAll(); key("", Qt.Key_V, Qt.ControlModifier)
                    field.cursorPosition = 0
                    stage = 4
                } else if (stage === 4 && !field.pasteBusy) {
                    expect(field.text === "newer", "paste overwrote moved selection")
                    field.selectAll(); key("", Qt.Key_V, Qt.ControlModifier)
                    field.text = "external"
                    stage = 5
                } else if (stage === 5 && !field.pasteBusy) {
                    expect(field.text === "external", "paste overwrote external refresh")
                    key("", Qt.Key_Z, Qt.ControlModifier)
                    expect(field.text === "external", "undo restored stale native settings")
                    expect(field.readOnly && !field.canPaste, "edit path made native editor writable")
                    console.log("HYPRVEIL_SAFE_INPUT_OK " + JSON.stringify({checks:checks, edits:edits}))
                    Qt.quit()
                }
            } catch (error) { console.error("HYPRVEIL_SAFE_INPUT_FAILED " + error); Qt.quit() }
            if (ticks > 200) { console.error("HYPRVEIL_SAFE_INPUT_FAILED timeout"); Qt.quit() }
        }
    }
}
'''

with tempfile.TemporaryDirectory(prefix='hyprveil-safe-input-') as temporary:
    root = Path(temporary)
    (root/'Commons').symlink_to('/usr/share/omarchy/shell/Commons')
    (root/'Ui').symlink_to('/usr/share/omarchy/shell/Ui')
    plugin = root/'plugin'; plugin.mkdir()
    for name in ('SafeTextField.qml', 'I18n.js'): (plugin/name).write_bytes((ROOT/name).read_bytes())
    (plugin/'clipboard-read').write_text('import time,json;time.sleep(.12);print(json.dumps({"ok":True,"text":"/tmp/новая иконка.png"}))')
    (root/'shell.qml').write_text(QML)
    runtime=root/'runtime';runtime.mkdir(mode=0o700)
    env=dict(os.environ,HOME=str(root),XDG_RUNTIME_DIR=str(runtime),QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',QT_QPA_PLATFORMTHEME='',QT_STYLE_OVERRIDE='Fusion')
    for name in ('WAYLAND_DISPLAY','DISPLAY','HYPRLAND_INSTANCE_SIGNATURE','DBUS_SESSION_BUS_ADDRESS'): env.pop(name,None)
    result=subprocess.run(['/usr/bin/quickshell','--no-color','--path',str(root)],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=10)
    report={'ok':result.returncode==0 and 'HYPRVEIL_SAFE_INPUT_OK ' in result.stdout and not any(word in result.stdout for word in ('HYPRVEIL_SAFE_INPUT_FAILED','TypeError','ReferenceError','Cannot assign','Unable to assign')),'output':result.stdout}
    (ROOT/'artifacts').mkdir(exist_ok=True)
    (ROOT/'artifacts/clipboard-qml-input.json').write_text(json.dumps(report,indent=2)+'\n')
    print(result.stdout)
    raise SystemExit(0 if report['ok'] else 1)
