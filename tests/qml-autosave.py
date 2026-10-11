#!/usr/bin/env python3
"""Exercise real QML autosave scheduling with isolated, delayed subprocesses.

No compositor, installed controller, user configuration or desktop bus is used.
The fixture records every argv and final state, rather than mocking QML methods.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

PLUGIN = Path(os.environ.get("HYPRVEIL_TEST_PLUGIN", Path(__file__).resolve().parents[1]))
SCENARIOS = ("during-configure", "during-query", "atomic-icon", "close-debounce",
             "close-inflight", "failure-recovery", "privacy-busy", "invalid-color",
             "queued-close", "queued-query-close", "focused-external-color", "motif-layout", "paths-commit", "custom-icon",
             "custom-source-clear", "image-controls", "invalid-path", "focused-external-path", "image-click-commit",
             "raw-shader-preset-close", "raw-icon-builtin-close", "shader-pending", "legacy-controls", "image-reset",
             "asset-placeholders", "icon-recovery")
DEFAULTS = {"variant": "prism", "color": "#ffffff", "grain": 50, "speed": 100,
            "darkness": 50, "eye": True, "eye_size": 80, "icon": "eye", "icon_opacity": 75,
            "mask_color": "#000000", "image_fit": "stretch", "shader_path": "", "icon_path": "", "image_path": ""}

CONTROLLER = r'''#!/usr/bin/python3
import json, os, pathlib, sys, time
home = pathlib.Path(os.environ["HOME"])
action = sys.argv[1]
previous = [json.loads(line) for line in (home / "commands.jsonl").read_text().splitlines()] if (home / "commands.jsonl").exists() else []
number = 1 + sum(row["action"] == action for row in previous)
record = {"action": action, "argv": sys.argv[1:], "number": number, "pid": os.getpid(), "time": time.monotonic(),
          "clean": all(key not in os.environ for key in ("PYTHONPATH", "BASH_ENV", "LD_PRELOAD", "LD_LIBRARY_PATH", "DBUS_SESSION_BUS_ADDRESS", "HYPRLAND_INSTANCE_SIGNATURE"))}
with (home / "commands.jsonl").open("a") as file:
    file.write(json.dumps(record) + "\n")
state = json.loads((home / "state.json").read_text())
extras = ("mask_color", "image_fit", "shader_path", "icon_path", "image_path")
if action == "status":
    if SCENARIO in ("during-query", "focused-external-color", "focused-external-path", "queued-query-close") and number == 2:
        if SCENARIO == "during-query":
            state["speed"] = 130
        elif SCENARIO == "focused-external-color":
            state["color"] = "#adcfc8"
        elif SCENARIO == "focused-external-path":
            state["shader_path"] = "/tmp/remote.frag"
        (home / "state.json").write_text(json.dumps(state))
        time.sleep(0.36)
    else:
        time.sleep(0.035)
    mode = (home / "mode.txt").read_text() if (home / "mode.txt").exists() else "black"
    appearance = {key: value for key, value in state.items() if key not in extras}
    render = {key: state[key] for key in extras}
    native_render = {"image_path": state["image_path"]} if SCENARIO == "legacy-controls" else render
    print(json.dumps({"loaded": True, "enabled": True, "load_supported": False, "persistence_supported": True,
        "desired_mode": mode, "appearance": appearance, **render,
        "status": {"session": "live", "local_dump": "disabled-in-live", "mode": mode, "spoiler_status": "pending" if SCENARIO == "shader-pending" and state["shader_path"] else "ready", "appearance": appearance, **native_render}}))
elif action == "configure":
    time.sleep(0.36)
    if SCENARIO == "failure-recovery" and number == 1:
        print("fixture refused persistence /secret/private.lua", file=sys.stderr)
        sys.exit(17)
    names = {"--variant": "variant", "--color": "color", "--grain": "grain", "--speed": "speed", "--darkness": "darkness",
             "--eye": "eye", "--eye-size": "eye_size", "--icon": "icon", "--icon-opacity": "icon_opacity", "--mask-color": "mask_color", "--image-fit": "image_fit",
             "--shader-path": "shader_path", "--icon-path": "icon_path", "--image-path": "image_path"}
    args = sys.argv[2:]
    if not args or len(args) % 2:
        sys.exit("malformed configure argv")
    if SCENARIO == "icon-recovery" and "--icon-path" in args and not pathlib.Path(args[args.index("--icon-path")+1]).is_file():
        print("fixture refused missing custom PNG before native mutation", file=sys.stderr)
        sys.exit(17)
    if SCENARIO == "legacy-controls" and (set(args[::2]) & {"--mask-color", "--image-fit", "--shader-path", "--icon-path"} or "--icon" in args and args[args.index("--icon")+1] == "custom"):
        sys.exit("old native refused new rendering fields")
    for flag, value in zip(args[::2], args[1::2]):
        key = names[flag]
        state[key] = value == "on" if key == "eye" else value if key in ("variant", "color", "icon", "mask_color", "image_fit", "shader_path", "icon_path", "image_path") else int(value)
    if (home / "mode.txt").exists() and (home / "mode.txt").read_text() == "image" and not state["image_path"]:
        sys.exit("image mode requires a nonempty PNG path")
    (home / "state.json").write_text(json.dumps(state))
    print(json.dumps({"appearance": state}))
elif action in ("black", "color", "image"):
    (home / "mode.txt").write_text(action)
    if action == "color": state["mask_color"] = sys.argv[2]
    elif action == "image":
        if SCENARIO == "legacy-controls" and len(sys.argv) != 3: sys.exit("old native image received unsupported options")
        state["image_path"] = sys.argv[2]
        if len(sys.argv) > 3: state["image_fit"] = sys.argv[4]
    (home / "state.json").write_text(json.dumps(state))
    print(json.dumps({"mode": action}))
else:
    sys.exit("unexpected fixture action")
'''

QML = r'''import QtQuick
import Quickshell
import "./plugin" as Plugin
ShellRoot {
    Item { id: host; property bool privacyBusy: false; property bool privacyDispatching: false
        property var focusPrivacy: ({state:"unknown",address:"",stable_id:"",native_private:false,inherited:false}) }
    Window { width: 510; height: 900; visible: true
        Plugin.Panel { id: panel; manageIpc: false; hostWidget: host
            controllerCommand: [Quickshell.env("HOME") + "/.local/bin/hyprveil"] }
    }
    property var editor: null
    property var popup: null
    property var hex: null
    property var pathField: null
    property int stage: 0
    property int ticks: 0
    property int checkpoint: 0
    property real initialHeight: 0
    property real maxHeightDelta: 0
    property int editableSamples: 0
    property int motifIndex: 0
    property var motifs: ["error404", "anonymous", "matrix"]
    function find(item, kind, name) {
        if (kind === "editor" && typeof item.advanced === "boolean" && item.draft !== undefined) return item
        if (kind === "popup" && item.contentWidth !== undefined && typeof item.fittedContentHeight === "function") return item
        if (kind === "icon" && item.modelData === name && typeof item.clicked === "function") return item
        if (kind === "preset" && item.modelData === name && typeof item.pick === "function") return item
        if (kind === "mode" && item.mode === name && typeof item.picked === "function") return item
        if (kind === "field" && item.objectName === name) return item
        if (kind === "hex" && item.objectName === "spoilerColor" && item.acceptableInput !== undefined && typeof item.textEdited === "function") return item
        for (var i=0;i<item.children.length;i++) { var child=find(item.children[i],kind,name); if(child) return child }
        return null
    }
    function edit(key, value) { editor.edited(key,value) }
    function checkAssetSources(item) {
        if (item.source !== undefined)
            expect(String(item.source).indexOf("untrusted.png")<0, "user FIFO reached a Qt source")
        for (var i=0;i<item.children.length;i++) checkAssetSources(item.children[i])
    }
    function settled() { return !panel.acting && !panel.querying && !panel.appearanceDirty && panel.submittedFields === null }
    function expect(value, reason) { if (!value) throw new Error(SCENARIO + ": " + reason + " stage=" + stage) }
    function finish() {
        expect(panel.current.known && panel.current.loaded, "lost attested current state")
        expect(!panel.appearanceSaveBlocked && !panel.appearanceDirty, "save not confirmed")
        expect(editableSamples > 0 || SCENARIO === "focused-external-color" || SCENARIO === "focused-external-path" || SCENARIO === "queued-query-close", "configure interval not observed")
        console.log("HYPRVEIL_AUTOSAVE_OK " + JSON.stringify({scenario:SCENARIO,editable_samples:editableSamples,max_height_delta:maxHeightDelta,closed:!panel.opened}))
        Qt.quit()
    }
    Component.onCompleted: panel.open()
    Timer {
        interval: 20; running: true; repeat: true
        onTriggered: {
            ticks++
            if (editor && panel.acting && panel.actionName === "configure") {
                expect(panel.current.known && editor.enabled && !editor.busy, "configure disabled controls or cleared known state")
                editableSamples++
                if (SCENARIO === "asset-placeholders") checkAssetSources(panel)
                if (panel.opened && SCENARIO !== "atomic-icon" && SCENARIO !== "custom-icon" && SCENARIO !== "icon-recovery" && SCENARIO !== "image-controls" && SCENARIO !== "image-click-commit" && !(SCENARIO === "legacy-controls" && panel.tab === "hide")) {
                    maxHeightDelta=Math.max(maxHeightDelta,Math.abs(popup.contentHeight-initialHeight))
                    expect(maxHeightDelta <= 1, "configure changed popup height")
                }
            }
            if (stage === 0 && panel.current.known && !panel.querying) {
                panel.setTab("customize")
                editor=find(panel,"editor",""); popup=find(panel,"popup",""); hex=find(panel,"hex","")
                expect(editor && popup && hex, "real editor controls not found")
                if (SCENARIO === "atomic-icon" || SCENARIO === "invalid-color" || SCENARIO === "motif-layout" || SCENARIO === "paths-commit" || SCENARIO === "custom-icon" || SCENARIO === "icon-recovery" || SCENARIO === "invalid-path" || SCENARIO === "focused-external-path" || SCENARIO === "raw-shader-preset-close" || SCENARIO === "raw-icon-builtin-close" || SCENARIO === "shader-pending" || SCENARIO === "legacy-controls") editor.advanced=true
                stage=1
            } else if (stage === 1) {
                initialHeight=popup.contentHeight
                if (SCENARIO === "asset-placeholders") {
                    checkAssetSources(panel)
                    var marker=find(editor,"field","customIconPlaceholder")
                    expect(marker.visible, "synthetic custom PNG icon marker missing")
                    panel.setTab("hide"); stage=36
                }
                else if (SCENARIO === "icon-recovery") {
                    find(editor,"icon","custom").clicked()
                    pathField=find(editor,"field","customIconPath")
                    pathField.forceActiveFocus(); pathField.text=Quickshell.env("HOME")+"/missing icon.png"; pathField.textEdited(); pathField.accepted()
                    stage=34
                }
                else if (SCENARIO === "legacy-controls") {
                    expect(!panel.current.assetsSupported && !editor.assetsSupported, "client defaults invented native asset support")
                    expect(!find(editor,"icon","custom").enabled && !find(editor,"field","customShaderPath").enabled && !find(editor,"field","customIconPath").enabled, "old native exposed custom files")
                    expect(!find(panel,"field","maskColor").enabled, "old native exposed mask color")
                    for (var fit of ["fill","fit","tile","stretch"]) expect(!find(panel,"icon",fit).enabled, "old native exposed image sizing")
                    expect(find(panel,"field","nativeUpdateNotice").visible, "old native lacks update guidance")
                    expect(find(panel,"mode","black").enabled && !find(panel,"mode","color"), "old native lost black or exposed Color")
                    panel.act("color"); edit("mask_color","#123456"); edit("icon","custom")
                    expect(!panel.acting && !panel.appearanceDirty, "unsupported new intent entered old native queue")
                    var builtin=find(editor,"preset","matrix"), shield=find(editor,"icon","shield")
                    expect(builtin.enabled && shield.enabled, "old native lost builtin appearance controls")
                    builtin.pick(); shield.clicked(); stage=30
                }
                else if (SCENARIO === "image-reset") {
                    expect(panel.current.assetsSupported && panel.current.mode === "image" && panel.appearanceDraft.image_path !== "", "image reset baseline missing")
                    panel.resetAppearance(); stage=33
                }
                else if (SCENARIO === "image-click-commit") {
                    panel.setTab("hide")
                    pathField=find(panel,"field","imagePath")
                    pathField.forceActiveFocus(); pathField.text=Quickshell.env("HOME")+"/second image.png"; pathField.textEdited()
                    find(panel,"mode","image").picked(); stage=8
                }
                else if (SCENARIO === "raw-shader-preset-close") {
                    pathField=find(editor,"field","customShaderPath")
                    pathField.forceActiveFocus(); pathField.text="/tmp/unwanted.frag"; pathField.textEdited()
                    find(editor,"preset","matrix").pick(); panel.close(); stage=8
                }
                else if (SCENARIO === "raw-icon-builtin-close") {
                    pathField=find(editor,"field","customIconPath")
                    pathField.forceActiveFocus(); pathField.text=Quickshell.env("HOME")+"/second image.png"; pathField.textEdited()
                    find(editor,"icon","lock").clicked(); panel.close(); stage=8
                }
                else if (SCENARIO === "paths-commit" || SCENARIO === "custom-icon" || SCENARIO === "image-controls" || SCENARIO === "shader-pending") {
                    if (SCENARIO === "paths-commit" || SCENARIO === "shader-pending") {
                        pathField=find(editor,"field","customShaderPath")
                        pathField.forceActiveFocus(); pathField.text=SCENARIO === "shader-pending" ? "/tmp/pending.frag" : "/tmp/first.frag"; pathField.textEdited()
                    } else if (SCENARIO === "custom-icon") {
                        find(editor,"icon","custom").clicked()
                        expect(!panel.appearanceDirty, "custom icon activated without a PNG path")
                        pathField=find(editor,"field","customIconPath")
                        expect(pathField.visible, "custom PNG path not exposed")
                        pathField.forceActiveFocus(); pathField.text=Quickshell.env("HOME")+"/pattern image#.png"; pathField.textEdited()
                    } else {
                        panel.setTab("hide")
                        pathField=find(panel,"field","imagePath")
                        pathField.forceActiveFocus(); pathField.text=Quickshell.env("HOME")+"/pattern image#.png"; pathField.textEdited()
                    }
                    checkpoint=ticks; stage=20
                }
                else if (SCENARIO === "custom-source-clear") { find(editor,"preset","matrix").pick(); stage=8 }
                else if (SCENARIO === "invalid-path") {
                    pathField=find(editor,"field","customShaderPath")
                    pathField.forceActiveFocus(); pathField.text="relative/shader.frag"; pathField.textEdited(); pathField.accepted()
                    expect(!panel.appearanceDirty && !editor.pathsValid, "invalid path entered the native queue")
                    edit("grain",17); edit("mask_color","#223344"); panel.close(); stage=8
                }
                else if (SCENARIO === "focused-external-path") {
                    pathField=find(editor,"field","customShaderPath")
                    pathField.forceActiveFocus(); panel.refresh(false); stage=25
                }
                else if (SCENARIO === "during-query") { panel.refresh(false); stage=2 }
                else if (SCENARIO === "motif-layout") {
                    expect(panel.appearanceDraft.variant==="prism" && panel.appearanceDraft.eye, "motif layout baseline changed")
                    find(editor,"preset",motifs[0]).pick(); stage=14
                }
                else if (SCENARIO === "queued-query-close") {
                    panel.refresh(false); panel.act("black"); panel.close(); stage=8
                }
                else if (SCENARIO === "focused-external-color") {
                    hex.forceActiveFocus(); panel.refresh(false); stage=12
                }
                else if (SCENARIO === "atomic-icon") {
                    var icon=find(editor,"icon","shield")
                    expect(icon && icon.visible && icon.enabled, "actual icon selector unavailable")
                    icon.clicked()
                    expect(panel.appearanceDraft.icon === "shield" && panel.appearanceDraft.eye, "icon visibility patch not atomic")
                    stage=8
                } else {
                    edit("grain",17)
                    if (SCENARIO === "close-debounce") { panel.close(); stage=8 }
                    else if (SCENARIO === "invalid-color") {
                        hex.forceActiveFocus(); hex.text="#12"; hex.textEdited()
                        expect(!editor.colorValid, "invalid color accepted")
                        var theme=find(editor,"preset","matrix"), lock=find(editor,"icon","lock")
                        expect(theme.enabled && lock.enabled, "incomplete color disabled unrelated controls")
                        theme.pick(); lock.clicked()
                        expect(!editor.colorValid, "other controls rewrote focused incomplete color")
                        panel.close(); stage=8
                    } else stage=3
                }
            } else if (stage === 36) {
                expect(find(find(panel,"mode","image"),"field","imageAssetPlaceholder").visible, "synthetic image marker missing")
                checkAssetSources(panel); panel.setTab("customize"); stage=37
            } else if (stage === 37) {
                checkAssetSources(panel); initialHeight=popup.contentHeight
                edit("grain",17); stage=8
            } else if (stage === 34 && panel.appearanceSaveBlocked && !panel.acting && !panel.querying) {
                expect(panel.appearanceDraft.icon_path.indexOf("missing icon.png")>0, "failed custom path intent missing")
                find(editor,"icon","lock").clicked(); stage=35
            } else if (stage === 35 && settled()) {
                expect(panel.current.appearance.icon==="lock" && panel.current.appearance.icon_path==="" && !panel.appearanceSaveBlocked, "builtin icon could not recover from rejected PNG")
                finish()
            } else if (stage === 30 && settled()) {
                expect(panel.current.appearance.variant==="matrix" && panel.current.appearance.icon==="shield", "old native builtin edits not confirmed")
                panel.resetAppearance(); stage=31
            } else if (stage === 31 && settled()) {
                expect(panel.current.appearance.variant==="prism" && panel.current.appearance.icon==="eye", "old native reset failed")
                panel.setTab("hide")
                pathField=find(panel,"field","imagePath")
                expect(pathField.enabled, "old native image path disabled")
                pathField.forceActiveFocus(); pathField.text=Quickshell.env("HOME")+"/pattern image#.png"; pathField.textEdited()
                find(panel,"mode","image").picked(); stage=32
            } else if (stage === 32 && settled()) {
                expect(panel.current.mode==="image" && !panel.current.assetsSupported, "old native Image lost compatibility")
                finish()
            } else if (stage === 33 && settled()) {
                expect(panel.current.mode==="image" && panel.current.appearance.image_path.indexOf("pattern image#.png")>0, "appearance reset cleared PNG or changed image mode")
                expect(panel.current.appearance.mask_color==="#224466" && panel.current.appearance.image_fit==="fit", "appearance reset changed background asset settings")
                expect(panel.current.appearance.variant==="prism" && panel.current.appearance.icon==="eye", "appearance reset did not restore builtin defaults")
                finish()
            } else if (stage === 20 && ticks-checkpoint>=8) {
                expect(!panel.appearanceDirty && !panel.acting, "path keystrokes saved before Enter/blur")
                if (SCENARIO === "image-controls") {
                    pathField.editingFinished()
                    for (var fit of ["fill","fit","stretch","tile"]) find(panel,"icon",fit).clicked()
                    var mask=find(panel,"field","maskColor")
                    mask.text="#224466"; mask.textEdited(); stage=22
                } else { pathField.accepted(); stage=SCENARIO === "paths-commit" ? 21 : 8 }
            } else if (stage === 21 && panel.acting && panel.actionName === "configure") {
                pathField.text="/tmp/latest.frag"; pathField.textEdited(); pathField.editingFinished()
                edit("mask_color","#345678"); edit("image_fit","fit"); panel.close(); stage=8
            } else if (stage === 22 && settled()) {
                expect(panel.current.appearance.image_fit==="tile" && panel.current.appearance.mask_color==="#224466", "image controls did not confirm")
                panel.act("color"); stage=23
            } else if (stage === 23 && !panel.acting && !panel.querying && panel.current.known) {
                expect(panel.current.mode==="color", "color mode not attested")
                panel.act("image"); stage=24
            } else if (stage === 24 && !panel.acting && !panel.querying && panel.current.known) {
                expect(panel.current.mode==="image" && panel.current.appearance.image_fit==="tile", "PNG mode/fit not attested")
                finish()
            } else if (stage === 25 && !panel.querying) {
                expect(panel.current.appearance.shader_path==="/tmp/remote.frag" && pathField.text==="/tmp/old.frag", "focused untouched path was overwritten during poll")
                editor.forceActiveFocus(); pathField.editingFinished(); checkpoint=ticks; stage=26
            } else if (stage === 26 && ticks-checkpoint>=8) {
                expect(pathField.text==="/tmp/remote.frag" && !panel.appearanceDirty && !panel.acting, "blur sent stale untouched path")
                finish()
            } else if (stage === 2 && panel.querying) {
                edit("grain",18); edit("grain",24)
                stage=8
            } else if (stage === 3 && panel.acting && panel.actionName === "configure") {
                if (SCENARIO === "during-configure") {
                    edit("grain",18); edit("grain",17); edit("grain",23)
                    var nextTheme=find(editor,"preset","matrix")
                    expect(nextTheme.enabled, "inflight configure disabled preset selector")
                    nextTheme.pick()
                    stage=8
                } else if (SCENARIO === "close-inflight") {
                    edit("grain",23); panel.close(); stage=8
                } else if (SCENARIO === "privacy-busy") {
                    host.privacyBusy=true; panel.close(); stage=4
                } else if (SCENARIO === "queued-close") {
                    panel.act("black"); panel.close(); stage=8
                } else stage=5
            } else if (stage === 4 && !panel.acting) {
                expect(host.privacyBusy && panel.submittedFields !== null, "busy acknowledgement overlap not exercised")
                checkpoint=ticks; stage=6
            } else if (stage === 6 && ticks-checkpoint>=8) {
                host.privacyBusy=false; stage=8
            } else if (stage === 5 && panel.appearanceSaveBlocked && !panel.acting && !panel.querying) {
                expect(panel.appearanceDirty && panel.appearanceDraft.grain===17 && panel.current.appearance.grain===50, "failure discarded dirty edit or claimed success")
                expect(panel.appearanceError.length>0 && panel.appearanceError.indexOf("/secret/")<0, "failure leaked diagnostics or lost error")
                checkpoint=ticks; panel.refresh(false); stage=7
            } else if (stage === 7) {
                expect(!panel.acting && panel.appearanceSaveBlocked && panel.appearanceDirty, "failure retried without new edit")
                if (ticks-checkpoint===8 || ticks-checkpoint===16) panel.refresh(false)
                if (ticks-checkpoint>=24 && !panel.querying) { edit("grain",24); stage=8 }
            } else if (stage === 14) {
                maxHeightDelta=Math.max(maxHeightDelta,Math.abs(popup.contentHeight-initialHeight))
                expect(maxHeightDelta<=1, "art motif or icon hint changed popup height")
                if (settled()) {
                    expect(panel.current.appearance.variant===motifs[motifIndex] && panel.current.appearance.eye, "motif not freshly confirmed with visible icon")
                    if (++motifIndex === motifs.length) finish()
                    else find(editor,"preset",motifs[motifIndex]).pick()
                }
            } else if (stage === 12 && !panel.querying) {
                expect(panel.current.appearance.color==="#adcfc8" && hex.text==="#ffffff", "focused untouched text did not preserve external native color")
                editor.forceActiveFocus(); checkpoint=ticks; stage=13
            } else if (stage === 13 && ticks-checkpoint>=2) {
                expect(hex.text==="#adcfc8" && !panel.appearanceDirty && !panel.acting, "blur overwrote external color or marked untouched text dirty")
                finish()
            } else if (stage === 8 && settled()) {
                var expected=SCENARIO === "during-configure" || SCENARIO === "close-inflight" ? 23 : SCENARIO === "during-query" || SCENARIO === "failure-recovery" ? 24 : SCENARIO === "atomic-icon" || SCENARIO === "queued-query-close" || SCENARIO === "paths-commit" || SCENARIO === "custom-icon" || SCENARIO === "custom-source-clear" || SCENARIO === "image-click-commit" || SCENARIO === "raw-shader-preset-close" || SCENARIO === "raw-icon-builtin-close" || SCENARIO === "shader-pending" ? 50 : 17
                expect(panel.current.appearance.grain===expected && panel.appearanceDraft.grain===expected, "latest edit was lost")
                if (SCENARIO === "shader-pending") expect(panel.current.mode==="spoiler" && panel.current.appearance.shader_path==="/tmp/pending.frag" && !panel.current.spoilerFallback && panel.appearanceError==="", "healthy pending shader save was rejected or marked as fallback")
                if (SCENARIO === "image-click-commit") expect(panel.current.mode==="image" && panel.current.appearance.image_path.indexOf("second image.png")>0, "image click used stale/uncommitted path")
                if (SCENARIO === "raw-shader-preset-close") expect(panel.current.appearance.shader_path==="" && panel.current.appearance.variant==="matrix" && !panel.opened, "close restored a discarded custom shader intent")
                if (SCENARIO === "raw-icon-builtin-close") expect(panel.current.appearance.icon==="lock" && panel.current.appearance.icon_path.indexOf("pattern image#.png")>0 && !panel.opened, "close restored a discarded custom icon intent")
                if (SCENARIO === "paths-commit") expect(panel.current.appearance.shader_path==="/tmp/latest.frag" && panel.current.appearance.image_fit==="fit" && panel.current.appearance.mask_color==="#345678" && !panel.opened, "new top-level edits were lost on close")
                if (SCENARIO === "custom-icon") expect(panel.current.appearance.icon==="custom" && panel.current.appearance.eye && panel.current.appearance.icon_path.indexOf("pattern image#.png")>0, "custom PNG icon patch not atomic")
                if (SCENARIO === "custom-source-clear") expect(panel.current.appearance.shader_path==="" && panel.current.appearance.variant==="matrix", "built-in selection did not clear custom shader")
                if (SCENARIO === "invalid-path") expect(panel.current.appearance.shader_path==="" && panel.current.appearance.mask_color==="#223344", "invalid path blocked valid edits")
                if (SCENARIO === "during-query") expect(panel.current.appearance.speed===130 && panel.appearanceDraft.speed===130, "untouched native field overwritten")
                if (SCENARIO === "during-configure") expect(panel.current.appearance.variant==="matrix", "latest variant was lost")
                if (SCENARIO === "invalid-color") expect(panel.current.appearance.color==="#ffffff" && panel.current.appearance.variant==="matrix" && panel.current.appearance.icon==="lock" && editor.colorValid && !panel.opened, "incomplete color prevented other saves or leaked into model")
                if (SCENARIO.indexOf("close-")===0 || SCENARIO === "privacy-busy" || SCENARIO === "queued-close" || SCENARIO === "queued-query-close") expect(!panel.opened, "closed save reopened panel")
                finish()
            }
            if (ticks>200) throw new Error(SCENARIO + ": autosave failed to settle stage=" + stage)
        }
    }
}
'''


def run_case(scenario):
    with tempfile.TemporaryDirectory(prefix="hyprveil-autosave-") as temporary:
        root = Path(temporary)
        (root / "Commons").symlink_to("/usr/share/omarchy/shell/Commons")
        ui = root / "Ui"
        ui.mkdir()
        for source in Path("/usr/share/omarchy/shell/Ui").iterdir():
            if source.name != "KeyboardPanel.qml":
                (ui / source.name).symlink_to(source)
        (ui / "KeyboardPanel.qml").write_text('''import QtQuick
Item {
    property Item anchorItem: null
    property QtObject bar: null
    property var owner: null
    property bool open: false
    property Item focusTarget: null
    property int contentWidth: 470
    property int contentHeight: 800
    width: contentWidth; height: contentHeight; visible: open
    function fittedContentWidth(v) { return v }
    function fittedContentHeight(v) { return v }
}
''')
        (root / "plugin").symlink_to(PLUGIN)
        home = root / "home"
        commands = home / ".local/bin"
        commands.mkdir(parents=True)
        state = dict(DEFAULTS)
        if scenario in ("atomic-icon", "custom-icon", "icon-recovery"):
            state.update(eye=False, icon="none")
        if scenario in ("custom-source-clear", "focused-external-path", "raw-shader-preset-close"):
            state["shader_path"] = "/tmp/old.frag"
        (home / "pattern image#.png").write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1cAAAAASUVORK5CYII="))
        (home / "second image.png").write_bytes((home / "pattern image#.png").read_bytes())
        if scenario == "raw-icon-builtin-close":
            state.update(icon="custom", icon_path=str(home / "pattern image#.png"))
        if scenario == "shader-pending":
            (home / "mode.txt").write_text("spoiler")
        if scenario == "image-reset":
            state.update(variant="matrix", icon="lock", grain=23, image_path=str(home / "pattern image#.png"), image_fit="fit", mask_color="#224466")
            (home / "mode.txt").write_text("image")
        if scenario == "asset-placeholders":
            fifo = home / "untrusted.png"
            os.mkfifo(fifo, 0o600)
            state.update(image_path=str(fifo), icon="custom", icon_path=str(fifo))
            (home / "mode.txt").write_text("image")
        (home / "state.json").write_text(json.dumps(state))
        controller = commands / "hyprveil"
        controller.write_text(CONTROLLER.replace("SCENARIO", repr(scenario)))
        controller.chmod(0o700)
        (root / "shell.qml").write_text(QML.replace("SCENARIO", json.dumps(scenario)))
        runtime = root / "runtime"
        runtime.mkdir(mode=0o700)
        environment = dict(os.environ, HOME=str(home), XDG_RUNTIME_DIR=str(runtime), QT_QPA_PLATFORM="offscreen",
                           QT_QUICK_BACKEND="software", QT_QPA_PLATFORMTHEME="", QT_STYLE_OVERRIDE="Fusion",
                           PYTHONPATH="/fixture-injection", BASH_ENV="/fixture-injection")
        for key in ("WAYLAND_DISPLAY", "DISPLAY", "HYPRLAND_INSTANCE_SIGNATURE", "DBUS_SESSION_BUS_ADDRESS"):
            environment.pop(key, None)
        started = time.monotonic()
        output = ""
        returncode = -1
        try:
            result = subprocess.run(["/usr/bin/quickshell", "--no-color", "--path", str(root)], env=environment,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=7)
            output, returncode = result.stdout, result.returncode
        except subprocess.TimeoutExpired as error:
            output = error.stdout.decode() if isinstance(error.stdout, bytes) else error.stdout or ""
        finally:
            log = [json.loads(line) for line in (home / "commands.jsonl").read_text().splitlines()] if (home / "commands.jsonl").exists() else []
            for record in log:
                try:
                    if str(controller).encode() in Path("/proc", str(record["pid"]), "cmdline").read_bytes().split(b"\0"):
                        os.kill(record["pid"], signal.SIGKILL)
                except (ProcessLookupError, FileNotFoundError):
                    pass
            leftovers = []
            for record in log:
                try:
                    if str(controller).encode() in Path("/proc", str(record["pid"]), "cmdline").read_bytes().split(b"\0"):
                        leftovers.append(record["pid"])
                except (FileNotFoundError, ProcessLookupError):
                    pass
        final = json.loads((home / "state.json").read_text())
        summary = {"scenario": scenario, "returncode": returncode, "seconds": round(time.monotonic()-started, 3),
                   "commands": log, "final": final, "output": output[-16384:]}
        summary["process_leftovers"] = leftovers
        summary["ok"] = returncode == 0 and "HYPRVEIL_AUTOSAVE_OK " in output and not any(
            word in output for word in ("TypeError", "ReferenceError", "Cannot assign", "Unable to assign", "Error:"))
        configurations = [row for row in log if row["action"] == "configure"]
        expected_count = 3 if scenario in ("motif-layout", "legacy-controls") else 0 if scenario in ("focused-external-color", "focused-external-path", "queued-query-close") else 2 if scenario in ("during-configure", "close-inflight", "failure-recovery", "paths-commit", "icon-recovery") else 1
        summary["ok"] &= len(configurations) == expected_count and all(row["clean"] for row in log) and not leftovers
        if scenario == "atomic-icon" and configurations:
            summary["ok"] &= dict(zip(configurations[0]["argv"][1::2], configurations[0]["argv"][2::2])) == {"--icon": "shield", "--eye": "on"}
        if scenario == "during-query" and configurations:
            summary["ok"] &= configurations[0]["argv"] == ["configure", "--grain", "24"] and final["speed"] == 130
        if scenario == "during-configure" and len(configurations) == 2:
            summary["ok"] &= dict(zip(configurations[1]["argv"][1::2], configurations[1]["argv"][2::2])) == {"--grain": "23", "--variant": "matrix"}
        if scenario == "invalid-color" and configurations:
            summary["ok"] &= "--color" not in configurations[0]["argv"] and final["color"] == "#ffffff" and final["variant"] == "matrix" and final["icon"] == "lock"
        if scenario == "queued-close":
            summary["ok"] &= [row["action"] for row in log if row["action"] != "status"] == ["configure", "black"]
        if scenario == "queued-query-close":
            summary["ok"] &= [row["action"] for row in log if row["action"] != "status"] == ["black"]
        if scenario == "focused-external-color":
            summary["ok"] &= all(row["action"] == "status" for row in log) and final["color"] == "#adcfc8"
        if scenario == "shader-pending" and configurations:
            summary["ok"] &= configurations[0]["argv"] == ["configure", "--shader-path", "/tmp/pending.frag"]
            summary["ok"] &= final["shader_path"] == "/tmp/pending.frag"
        if scenario == "image-click-commit":
            mutations = [row for row in log if row["action"] != "status"]
            summary["ok"] &= [row["action"] for row in mutations] == ["image", "configure"]
            summary["ok"] &= mutations[0]["argv"] == ["image", str(home / "second image.png"), "--fit", "stretch"]
        if scenario == "raw-shader-preset-close" and configurations:
            summary["ok"] &= configurations[0]["argv"] == ["configure", "--variant", "matrix", "--shader-path", ""]
        if scenario == "raw-icon-builtin-close" and configurations:
            summary["ok"] &= configurations[0]["argv"] == ["configure", "--icon", "lock"]
        if scenario == "paths-commit" and len(configurations) == 2:
            summary["ok"] &= configurations[0]["argv"] == ["configure", "--shader-path", "/tmp/first.frag"]
            summary["ok"] &= dict(zip(configurations[1]["argv"][1::2], configurations[1]["argv"][2::2])) == {"--shader-path": "/tmp/latest.frag", "--mask-color": "#345678", "--image-fit": "fit"}
        if scenario == "custom-icon" and configurations:
            summary["ok"] &= dict(zip(configurations[0]["argv"][1::2], configurations[0]["argv"][2::2])) == {"--icon": "custom", "--icon-path": str(home / "pattern image#.png"), "--eye": "on"}
        if scenario == "custom-source-clear" and configurations:
            summary["ok"] &= configurations[0]["argv"] == ["configure", "--variant", "matrix", "--shader-path", ""]
        if scenario == "invalid-path" and configurations:
            summary["ok"] &= dict(zip(configurations[0]["argv"][1::2], configurations[0]["argv"][2::2])) == {"--grain": "17", "--mask-color": "#223344"}
        if scenario == "image-controls":
            summary["ok"] &= [row["action"] for row in log if row["action"] != "status"] == ["configure", "color", "image"]
            summary["ok"] &= final["image_fit"] == "tile" and final["color"] == "#ffffff" and final["mask_color"] == "#224466"
        if scenario == "focused-external-path":
            summary["ok"] &= all(row["action"] == "status" for row in log) and final["shader_path"] == "/tmp/remote.frag"
        if scenario == "motif-layout":
            summary["ok"] &= [row["argv"] for row in configurations] == [["configure", "--variant", variant] for variant in ("error404", "anonymous", "matrix")]
        if scenario == "legacy-controls":
            forbidden = {"--mask-color", "--image-fit", "--shader-path", "--icon-path"}
            summary["ok"] &= all(not forbidden.intersection(row["argv"]) for row in configurations)
            summary["ok"] &= [row["argv"] for row in log if row["action"] == "image"] == [["image", str(home / "pattern image#.png")]]
            summary["ok"] &= [row["action"] for row in log if row["action"] != "status"] == ["configure", "configure", "image", "configure"]
            summary["ok"] &= final["image_path"] == str(home / "pattern image#.png") and final["variant"] == "prism" and final["icon"] == "eye"
        if scenario == "image-reset":
            summary["ok"] &= all("--image-path" not in row["argv"] for row in configurations)
            summary["ok"] &= final["image_path"] == str(home / "pattern image#.png") and final["image_fit"] == "fit" and final["mask_color"] == "#224466"
        if scenario == "asset-placeholders":
            summary["ok"] &= final["image_path"] == str(home / "untrusted.png") and final["icon_path"] == str(home / "untrusted.png")
        if scenario == "icon-recovery" and len(configurations) == 2:
            summary["ok"] &= configurations[0]["argv"] == ["configure", "--icon", "custom", "--icon-path", str(home / "missing icon.png"), "--eye", "on"]
            summary["ok"] &= configurations[1]["argv"] == ["configure", "--icon", "lock", "--eye", "on"]
            summary["ok"] &= final["icon"] == "lock" and final["icon_path"] == "" and final["eye"]
        return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", action="append", choices=SCENARIOS)
    parser.add_argument("--report", type=Path)
    options = parser.parse_args()
    sources = ("Panel.qml", "AppearanceEditor.qml", "Appearance.js", "I18n.js", "State.js", "SpoilerPreview.qml", "PrivacyIcon.qml", "StyleRow.qml")
    before = {name: hashlib.sha256((PLUGIN / name).read_bytes()).hexdigest() for name in sources}
    results = []
    for scenario in options.scenario or SCENARIOS:
        result = run_case(scenario)
        results.append(result)
        print("passed" if result["ok"] else "FAILED", scenario, flush=True)
        if not result["ok"]:
            print(result["output"], flush=True)
            print(json.dumps(result["commands"], indent=2), flush=True)
    after = {name: hashlib.sha256((PLUGIN / name).read_bytes()).hexdigest() for name in sources}
    source_stable = before == after
    ok = all(row["ok"] for row in results) and source_stable
    if options.report:
        options.report.parent.mkdir(parents=True, exist_ok=True)
        options.report.write_text(json.dumps({"ok": ok, "source_stable": source_stable,
                                             "source_sha256": after, "cases": results}, indent=2) + "\n")
    if not source_stable:
        print("FAILED: imported QML/JS changed during test run")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
